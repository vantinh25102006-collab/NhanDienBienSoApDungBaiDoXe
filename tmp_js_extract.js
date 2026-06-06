

  const API_BASE = '';

  let currentMode = 'IN'; // IN | OUT
  let lastRecognizedPlate = '';
  let comboPayload = null; // store last error payload / active list

  const elPlate = document.getElementById('plate');
  const elImage = document.getElementById('image');
  const elImagePreview = document.getElementById('imagePreview');
  const elResult = document.getElementById('result');

  const elModeBadge = document.getElementById('modeBadge');
  const elToggleModeBtn = document.getElementById('toggleModeBtn');
  const elActionBtn = document.getElementById('actionBtn');

  const elComboBoxWrap = document.getElementById('comboBoxWrap');
  const elComboSelect = document.getElementById('comboSelect');

  function setResult(obj) {
    elResult.textContent = JSON.stringify(obj, null, 2);
  }

  async function postForm(url, form) {
    const res = await fetch(url, { method: 'POST', body: form });
    const text = await res.text();
    let json;
    try { json = JSON.parse(text); } catch { json = { raw: text }; }
    if (!res.ok) {
      setResult({ status: res.status, error: json });
      return { ok: false, status: res.status, json };
    }
    setResult(json);
    return { ok: true, json };
  }

  function formatDateTime(isoSeconds) {
    try {
      const d = new Date(isoSeconds);
      if (isNaN(d.getTime())) return isoSeconds;
      return d.toLocaleString('vi-VN');
    } catch {
      return isoSeconds;
    }
  }

  function hoursFromSeconds(sec) {
    if (sec === null || sec === undefined) return '-';
    const h = sec / 3600;
    return (Math.round(h * 10) / 10).toFixed(1);
  }

  function hideComboBox() {
    elComboBoxWrap.style.display = 'none';
    elComboSelect.innerHTML = '';
    comboPayload = null;
  }

  // ===== Spots modal & spot detail =====
  let spotsDataCache = null;
  let activeItemsCache = null;

  const elSpotsModal = document.getElementById('spotsModal');
  const elSpotsGrid = document.getElementById('spotsGrid');
  const elSpotsError = document.getElementById('spotsError');

  const elSpotDetailModal = document.getElementById('spotDetailModal');
  const elSpotDetailTitle = document.getElementById('spotDetailTitle');
  const elSpotDetailSubtitle = document.getElementById('spotDetailSubtitle');
  const elSpotDetailImage = document.getElementById('spotDetailImage');
  const elSpotDetailImageHint = document.getElementById('spotDetailImageHint');
  const elSpotDetailInfo = document.getElementById('spotDetailInfo');

  async function loadSpotsAndActive() {
    const [spotsRes, activeRes] = await Promise.all([
      fetch(API_BASE + '/spots'),
      fetch(API_BASE + '/active')
    ]);
    const spotsJson = await spotsRes.json();
    const activeJson = await activeRes.json();
    return {
      spots: spotsJson.items || [],
      active: activeJson.items || [],
    };
  }

  function plateOrDash(s) {
    return (s || '').toString().trim() || '-';
  }

  function closeSpotsModal() {
    if (elSpotsModal) elSpotsModal.style.display = 'none';
    spotsDataCache = null;
    activeItemsCache = null;
  }

  function closeSpotDetailModal() {
    if (elSpotDetailModal) elSpotDetailModal.style.display = 'none';
  }

  // ===== Expanded “spot select” panel (đẩy 30% sang trái) =====
  let spotsExpanded = false;
  let selectedSpotId = null;
  let spotsPanelData = null; // { spots, active }

  function ensureExpandedLayout() {
    const wrapper = document.querySelector('.wrap');
    const grid2 = document.querySelector('.grid2');
    if (!wrapper || !grid2) return;

    // Update layout: grid2 currently 1.1fr 0.9fr. When expanded, shift to include left panel.
    if (spotsExpanded) {
      grid2.style.gridTemplateColumns = '0.6fr 0.4fr';
    } else {
      grid2.style.gridTemplateColumns = '1.1fr 0.9fr';
    }
  }

  function openExpandedPanelForSpot(activeItem) {
    if (!activeItem) return;
    selectedSpotId = activeItem.spot_id;
    spotsExpanded = true;
    ensureExpandedLayout();

    // Fill panel on left: we reuse the spotDetailModal UI content logic.
    // Create panel container lazily.
    let panel = document.getElementById('spotsInlinePanel');
    if (!panel) {
      // Insert panel into first card (functions area) left side by adding a new div above it.
      // Overlay panel on top of the spots grid.
      const modalRoot = document.getElementById('spotsModal');
      if (!modalRoot) return;
      // NOTE: cần đảm bảo panel không dùng biến modalInner cũ
      panel = document.createElement('div');

      panel.style.position = 'absolute';
      panel.style.top = '64px';
      panel.style.right = '16px';
      panel.style.width = '320px';
      panel.style.zIndex = '10000';
      panel.style.maxHeight = 'calc(100% - 84px)';
      panel.style.overflow = 'auto';
      panel.id = 'spotsInlinePanel';
      panel.style.marginTop = '12px';
      panel.style.padding = '12px';
      panel.style.border = '1px solid #eef2f7';
      panel.style.borderRadius = '12px';
      panel.style.background = '#fff';
      panel.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px;">
          <div>
            <b>Thông tin xe tại spot</b>
            <div style="font-size:12px;opacity:.85;margin-top:4px;" id="inlinePanelSub">Đang chọn...</div>
          </div>
          <button class="btn-secondary" style="width:auto;padding:8px 12px;background:#374151;" onclick="closeExpandedSpotsPanel()">-</button>
        </div>
        <div id="inlinePanelInfo" style="font-size:13px;line-height:1.6;" ></div>
        <div id="inlinePanelImageWrap" style="margin-top:10px;">
          <img id="inlinePanelImage" style="width:100%;max-height:180px;object-fit:contain;border:1px dashed #cbd5e1;border-radius:12px;background:#f8fafc;" />
          <div class="muted" style="margin-top:8px;" id="inlinePanelImageHint"></div>
        </div>
      `;
      modalRoot.appendChild(panel);
    }

    const spotId = activeItem.spot_id;
    const plate = activeItem.plate;
    const timeIn = activeItem.time_in;
    const lastImagePath = activeItem.last_image_path;

    document.getElementById('inlinePanelSub').textContent = `Spot ${spotId}`;
    document.getElementById('inlinePanelInfo').innerHTML = `
      <div><b>Biển số:</b> ${plateOrDash(plate)}</div>
      <div><b>Ngày giờ vào:</b> ${formatDateTime(timeIn || '')}</div>
      <div><b>Vị trí:</b> ${spotId || '-'}</div>
    `;

    const img = document.getElementById('inlinePanelImage');
    const hint = document.getElementById('inlinePanelImageHint');
    if (lastImagePath) {
      const filename = lastImagePath.split(/[/\\]/).pop();
      img.src = API_BASE + `/tmp_uploads/${encodeURIComponent(filename)}`;
      hint.textContent = 'Ảnh nhận diện từ upload gần nhất.';
    } else {
      img.removeAttribute('src');
      hint.textContent = 'Chưa có ảnh nhận diện cho spot này.';
    }
  }

  function closeExpandedSpotsPanel() {
    spotsExpanded = false;
    selectedSpotId = null;
    ensureExpandedLayout();
    const panel = document.getElementById('spotsInlinePanel');
    if (panel) panel.remove();
  }

  // Expose to inline onclick
  window.closeExpandedSpotsPanel = closeExpandedSpotsPanel;



  async function openSpotsModal() {
    if (!elSpotsModal) return;
    elSpotsModal.style.display = 'block';

    elSpotsGrid.innerHTML = '';
    elSpotsError.style.display = 'none';

    elSpotsGrid.innerHTML = '<div class="muted">Đang tải...</div>';

    try {
      const data = await loadSpotsAndActive();
      spotsDataCache = data.spots;
      activeItemsCache = data.active;

      renderSpotsGrid();
    } catch (e) {
      elSpotsError.style.display = 'block';
      elSpotsGrid.innerHTML = '';
    }
  }

  function renderSpotsGrid() {
    if (!spotsDataCache) return;

    const activeBySpot = {};
    (activeItemsCache || []).forEach(it => {
      if (it.spot_id) activeBySpot[it.spot_id] = it;
    });

    // Determine columns by max spot count; keep 10 columns like modal css
    const total = spotsDataCache.length;
    const items = total ? spotsDataCache : [];

    elSpotsGrid.innerHTML = '';

    if (!items.length) {
      elSpotsError.style.display = 'block';
      elSpotsGrid.innerHTML = '';
      return;
    }

    items.forEach((sp, idx) => {
      const spotId = sp.spot_id;
      const active = activeBySpot[spotId];
      const hasCar = !!active;

      // color: red if has car, green if empty (white/transparent for non-active if you want)
      let bg = '#22c55e';
      if (hasCar) bg = '#dc2626';
      else {
        // if is_active false => white
        if (sp.is_active === 0) bg = '#f3f4f6';
      }

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = spotId;
      btn.style.width = '100%';
      btn.style.height = '44px';
      btn.style.borderRadius = '8px';
      btn.style.border = '1px solid #e5e7eb';
      btn.style.cursor = hasCar ? 'pointer' : 'default';
      btn.style.background = bg;
      btn.style.color = hasCar ? '#fff' : '#111827';
      btn.style.fontWeight = '800';
      btn.style.display = 'flex';
      btn.style.alignItems = 'center';
      btn.style.justifyContent = 'center';
      btn.style.padding = '0';

      if (hasCar) {
        btn.addEventListener('click', () => {
          console.log('[spots] click spot', sp.spot_id, active);
          openExpandedPanelForSpot(active);
        });
      } else {
        btn.disabled = true;
        btn.style.opacity = '0.95';
      }

      elSpotsGrid.appendChild(btn);
    });
  }

  function openSpotDetail(activeItem) {
    if (!activeItem) return;

    const spotId = activeItem.spot_id;
    const plate = activeItem.plate;
    const timeIn = activeItem.time_in;

    elSpotDetailTitle.textContent = `Spot ${spotId} - ${plate}`;
    elSpotDetailSubtitle.textContent = `Đang đỗ từ: ${formatDateTime(timeIn || '')}`;

    const lastImagePath = activeItem.last_image_path;
    if (lastImagePath) {
      const filename = lastImagePath.split(/[/\\]/).pop();
      elSpotDetailImage.src = API_BASE + `/tmp_uploads/${encodeURIComponent(filename)}`;
      elSpotDetailImageHint.textContent = 'Ảnh nhận diện từ upload gần nhất.';
    } else {
      elSpotDetailImage.removeAttribute('src');
      elSpotDetailImageHint.textContent = 'Chưa có ảnh nhận diện cho spot này.';
    }

    elSpotDetailInfo.innerHTML = `
      <div><b>Biển số:</b> ${plateOrDash(plate)}</div>
      <div><b>Ngày giờ vào:</b> ${formatDateTime(timeIn || '')}</div>
      <div><b>Vị trí:</b> ${spotId || '-'}</div>
    `;

    elSpotDetailModal.style.display = 'block';
  }


  // ===== Modal details (active/history) =====

  // Ghi chú: phần modal được thêm mới. Đảm bảo không phá các hàm cũ (combo/check-in/out).
  const elDetailsModal = document.getElementById('detailsModal');
  const elModalTitle = document.getElementById('modalTitle');
  const elModalSubtitle = document.getElementById('modalSubtitle');
  const elTimeFrom = document.getElementById('timeFrom');
  const elTimeTo = document.getElementById('timeTo');
  const elPlateQuery = document.getElementById('plateQuery');
  const elModalHeadRow = document.getElementById('modalHeadRow');
  const elModalBody = document.getElementById('modalBody');


  let modalMode = 'active'; // active | history
  let modalItemsCache = []; // data loaded

  function openDetailsModal(mode) {
    modalMode = mode;
    elModalTitle.textContent = (mode === 'active') ? 'Chi tiết xe đang đỗ' : 'Chi tiết lịch sử đổ xe';
    elModalSubtitle.textContent = 'Lọc theo thời gian và/hoặc biển số. Kết quả cập nhật realtime.';

    // reset inputs
    elTimeFrom.value = '';
    elTimeTo.value = '';
    elPlateQuery.value = '';

    elDetailsModal.style.display = 'block';

    // load data once opened
    loadModalDataAndRender();
  }

  function closeDetailsModal() {
    elDetailsModal.style.display = 'none';
    modalItemsCache = [];
  }

  function parseDatetimeLocal(value) {
    // value example: "2026-06-06T10:30"
    if (!value) return null;
    const d = new Date(value);
    if (isNaN(d.getTime())) return null;
    return d;
  }

  function dateInRange(date, fromDate, toDate) {
    if (!date) return false;
    const t = date.getTime();
    if (fromDate && t < fromDate.getTime()) return false;
    if (toDate && t > toDate.getTime()) return false;
    return true;
  }

  function normalizePlate(s) {
    return (s || '').toString().trim().toUpperCase();
  }

  function getSearchPlateQuery() {
    return normalizePlate(elPlateQuery.value);
  }

  function filterItems(items) {
    const qPlate = getSearchPlateQuery();
    const fromDate = parseDatetimeLocal(elTimeFrom.value);
    const toDate = parseDatetimeLocal(elTimeTo.value);

    return (items || []).filter(it => {
      // plate partial match ("ghi tới đâu" -> filter realtime)
      if (qPlate) {
        const p = normalizePlate(it.plate);
        if (!p.includes(qPlate)) return false;
      }

      // time filter
      if (fromDate || toDate) {
        if (modalMode === 'active') {
          const t = it.time_in ? new Date(it.time_in) : null;
          if (!dateInRange(t, fromDate, toDate)) return false;
        } else {
          // history: use time_out if exists else time_in
          const timeStr = it.time_out || it.time_in;
          const t = timeStr ? new Date(timeStr) : null;
          if (!dateInRange(t, fromDate, toDate)) return false;
        }
      }

      return true;
    });
  }

  function renderModalTable(items) {
    const data = items || [];

    if (modalMode === 'active') {
      elModalHeadRow.innerHTML = `
        <tr>
          <th>Biển số</th>
          <th>Ngày giờ vào</th>
          <th>Vị trí</th>
        </tr>
      `;
      elModalBody.innerHTML = data.length ? data.map(it => `
        <tr>
          <td><b>${it.plate || ''}</b></td>
          <td>${formatDateTime(it.time_in || '')}</td>
          <td>${it.spot_id || '-'}</td>
        </tr>
      `).join('') : '<tr><td colspan="3" class="muted">Không có kết quả.</td></tr>';
    } else {
      elModalHeadRow.innerHTML = `
        <tr>
          <th>Biển số</th>
          <th>Đổ (IN)</th>
          <th>Lấy (OUT)</th>
          <th>Giờ</th>
          <th>Tiền</th>
        </tr>
      `;

      elModalBody.innerHTML = data.length ? data.map(it => {
        const timeIn = it.time_in ? formatDateTime(it.time_in) : '-';
        const timeOut = it.time_out ? formatDateTime(it.time_out) : '-';
        const durationSec = it.duration_seconds;
        const hours = (durationSec === null || durationSec === undefined) ? '-' : hoursFromSeconds(durationSec);
        const fee = it.fee_vnd === null || it.fee_vnd === undefined ? '-' : `${Number(it.fee_vnd).toLocaleString('vi-VN')} VND`;
        return `
          <tr>
            <td><b>${it.plate || ''}</b></td>
            <td>${timeIn}</td>
            <td>${timeOut}</td>
            <td>${hours}</td>
            <td>${fee}</td>
          </tr>
        `;
      }).join('') : '<tr><td colspan="5" class="muted">Không có kết quả.</td></tr>';
    }
  }

  function onPlateQueryChange() {
    if (!modalItemsCache) return;
    const filtered = filterItems(modalItemsCache);
    renderModalTable(filtered);
  }

  function applyTimeFilter() {
    if (!modalItemsCache) return;
    const filtered = filterItems(modalItemsCache);
    renderModalTable(filtered);
  }

  // close modal on ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && elDetailsModal && elDetailsModal.style.display !== 'none') {
      closeDetailsModal();
    }
  });

  // click outside to close
  if (elDetailsModal) {
    elDetailsModal.addEventListener('click', (e) => {
      if (e.target === elDetailsModal) {
        closeDetailsModal();
      }
    });
  }


  async function loadModalDataAndRender() {
    // show loading
    elModalBody.innerHTML = '<tr><td class="muted" colspan="5">Đang tải...</td></tr>';

    if (modalMode === 'active') {
      modalItemsCache = await fetchActiveItems();
    } else {
      const res = await fetch(API_BASE + '/history');
      const json = await res.json();
      modalItemsCache = json.items || [];
    }

    // first render without filters
    const filtered = filterItems(modalItemsCache);
    renderModalTable(filtered);
  }


  function showComboBox(items, plate) {
    elComboSelect.innerHTML = '';
    (items || []).forEach((it, idx) => {
      const opt = document.createElement('option');
      opt.value = String(idx);
      opt.textContent = `${it.spot_id || '-'} | ${formatDateTime(it.time_in)}`;
      elComboSelect.appendChild(opt);
    });

    comboPayload = { items, plate };
    elComboBoxWrap.style.display = 'block';
  }

  async function recognizeFromImage(file) {
    const form = new FormData();
    form.append('image', file);
    const res = await postForm(API_BASE + '/recognize', form);
    if (!res.ok) return null;
    const plate = (res.json.plate || '').toString().trim().toUpperCase();
    return plate;
  }

  async function onImageSelected() {
    hideComboBox();

    const file = elImage.files && elImage.files[0];
    if (!file) return;

    // Preview
    const url = URL.createObjectURL(file);
    elImagePreview.src = url;

    // IMPORTANT: Recognize immediately, then lock plate
    // Reset plate first to avoid stale value/lock issues
    elPlate.disabled = false;
    elPlate.value = '';
    lastRecognizedPlate = '';

    setResult({ status: 'recognizing', message: 'Đang nhận diện...' });

    const plate = await recognizeFromImage(file);
    if (!plate) {
      setResult({ status: 'error', message: 'Không nhận diện được biển số từ ảnh.' });
      // keep locked behavior? requirement says unlock until recognize; we'll unlock to allow manual fallback
      elPlate.disabled = false;
      return;
    }

    lastRecognizedPlate = plate;
    elPlate.value = plate;
    elPlate.disabled = true;

    // Update active list immediately
    await loadActiveTable();
  }

  elImage.addEventListener('change', onImageSelected);

  function toggleMode() {
    currentMode = (currentMode === 'IN') ? 'OUT' : 'IN';

    if (currentMode === 'IN') {
      elActionBtn.className = 'btn-primary';
      elActionBtn.textContent = 'Check-in';
      elModeBadge.textContent = 'CHECK-IN';
      elToggleModeBtn.textContent = 'Switch to CHECK-OUT';
    } else {
      elActionBtn.className = 'btn-danger';
      elActionBtn.textContent = 'Check-out';
      elModeBadge.textContent = 'CHECK-OUT';
      elToggleModeBtn.textContent = 'Switch to CHECK-IN';
    }

    hideComboBox();
    setResult({ status: 'mode', mode: currentMode });
  }

  async function performActionWithCombo() {
    if (!comboPayload) return;
    hideComboBox();

    // For now backend check-in/out logic only needs plate (and image if provided).
    // combo box is for UX message requirement; we still perform action using selected plate.
    await performAction();
  }

  async function performAction() {
    hideComboBox();

    const plate = (elPlate.value || '').trim().toUpperCase();
    const file = elImage.files && elImage.files[0];

    if (!plate) {
      setResult({ status: 'error', message: 'Chưa có biển số. Hãy upload ảnh để nhận diện.' });
      return;
    }
    if (!file) {
      setResult({ status: 'error', message: 'Chưa có ảnh. Hãy upload ảnh trước.' });
      return;
    }

    const form = new FormData();
    form.append('plate', plate);
    form.append('image', file);

    const url = (currentMode === 'IN') ? API_BASE + '/check-in' : API_BASE + '/check-out';

    const res = await postForm(url, form);
    if (!res.ok) {
      // combo box case: plate already inside when IN
      const err = res.json || {};
      const msg = (err.message || '').toString();

      if (msg.toLowerCase().includes('already inside') || msg.toLowerCase().includes('tồn tại')) {
        const activeItems = await fetchActiveItems();
        const same = (activeItems || []).filter(x => (x.plate || '').toString().trim().toUpperCase() === plate);
        if (same.length === 0) {
          setResult({ status: 'error', message: msg, plate });
          return;
        }
        showComboBox(same, plate);
        setResult({ status: 'error', message: msg, plate, combo: true });
        return;
      }

      setResult({ status: 'error', message: msg || 'Có lỗi xảy ra', plate });
      return;
    }

    // Success: refresh tables
    await loadActiveTable();
    await loadHistoryTable();
  }

  async function fetchActiveItems() {
    const res = await fetch(API_BASE + '/active');
    const json = await res.json();
    return json.items || [];
  }

  function selectRow(tbodyEl, trEl) {
    if (!tbodyEl || !trEl) return;
    Array.from(tbodyEl.querySelectorAll('tr')).forEach(r => r.style.outline = 'none');
    trEl.style.outline = '2px solid #2563eb';
  }

  let focusRowState = {
    section: null, // 'active' | 'history'
    plate: null,
    event_id: null,
    spot_id: null,
    time_in: null,
    time_out: null,
    status: null,
  };

  function openEditPlateModalForActive(activeItem) {
    focusRowState = {
      section: 'active',
      plate: activeItem.plate,
      event_id: null,
      spot_id: activeItem.spot_id || null,
      time_in: activeItem.time_in || null,
      time_out: null,
      status: 'IN',
    };

    document.getElementById('editPlateTitle').textContent = 'Sửa biển số xe đang đỗ';
    document.getElementById('editPlateSubtitle').textContent = `Spot ${activeItem.spot_id || '-'} · Đang đỗ từ ${formatDateTime(activeItem.time_in || '')}`;
    document.getElementById('editInfoText').innerHTML = `
      <div><b>Biển số hiện tại:</b> ${activeItem.plate || '-'}</div>
      <div><b>Vị trí:</b> ${activeItem.spot_id || '-'}</div>
      <div><b>Ngày giờ vào:</b> ${formatDateTime(activeItem.time_in || '')}</div>
    `;
    document.getElementById('editStatusText').textContent = 'Đang có xe (active_vehicles).';
    document.getElementById('editPlateInput').value = (activeItem.plate || '').toString().trim();

    document.getElementById('editPlateModal').style.display = 'block';
    document.getElementById('editPlateInput').disabled = false;
    setTimeout(() => document.getElementById('editPlateInput').focus(), 0);
  }

  function openEditPlateModalForHistory(historyItem) {
    focusRowState = {
      section: 'history',
      plate: historyItem.plate,
      event_id: historyItem.event_id,
      spot_id: historyItem.spot_id || null,
      time_in: historyItem.time_in || null,
      time_out: historyItem.time_out || null,
      status: historyItem.status || null,
    };

    const statusText = (historyItem.status === 'IN') ? 'Đang đổ (IN)' : 'Đã xử lý (OUT)';
    document.getElementById('editPlateTitle').textContent = 'Sửa biển số trong lịch sử';
    document.getElementById('editPlateSubtitle').textContent = `event_id=${historyItem.event_id} · ${statusText}`;
    document.getElementById('editInfoText').innerHTML = `
      <div><b>Biển số hiện tại:</b> ${historyItem.plate || '-'}</div>
      <div><b>Spot:</b> ${historyItem.spot_id || '-'}</div>
      <div><b>IN:</b> ${formatDateTime(historyItem.time_in || '')}</div>
      <div><b>OUT:</b> ${formatDateTime(historyItem.time_out || '')}</div>
    `;
    document.getElementById('editStatusText').textContent = statusText + '.';
    document.getElementById('editPlateInput').value = (historyItem.plate || '').toString().trim();

    document.getElementById('editPlateModal').style.display = 'block';
    document.getElementById('editPlateInput').disabled = false;
    setTimeout(() => document.getElementById('editPlateInput').focus(), 0);
  }

  function closeEditPlateModal() {
    document.getElementById('editPlateModal').style.display = 'none';
    focusRowState = { section: null, plate: null, event_id: null, spot_id: null, time_in: null, time_out: null, status: null };
  }

  window.closeEditPlateModal = closeEditPlateModal;

  async function saveEditPlate() {
    const newPlate = (document.getElementById('editPlateInput').value || '').trim().toUpperCase();
    if (!newPlate) {
      setResult({ status: 'error', message: 'Biển số không được rỗng.' });
      return;
    }

    if (focusRowState.section === 'active') {
      const form = new FormData();
      form.append('old_plate', focusRowState.plate);
      form.append('new_plate', newPlate);

      const res = await postForm(API_BASE + '/active/update-plate', form);
      if (!res.ok) return;
    } else if (focusRowState.section === 'history') {
      const form = new FormData();
      form.append('event_id', String(focusRowState.event_id));
      form.append('new_plate', newPlate);

      const res = await postForm(API_BASE + '/history/update-plate', form);
      if (!res.ok) return;
    } else {
      return;
    }

    closeEditPlateModal();
    await loadActiveTable();
    await loadHistoryTable();
    // refresh spots to reflect any state change
    await openSpotsModal();
    if (document.getElementById('spotsModal') && document.getElementById('spotsModal').style.display === 'block') {
      // already open; openSpotsModal refreshed grids
    }
  }

  window.saveEditPlate = saveEditPlate;

  // ===== Delete helpers (truyền trực tiếp tham số, không phụ thuộc focusRowState) =====
  async function deleteActiveByPlate(plate) {
    const p = (plate || '').toString().trim().toUpperCase();
    if (!p) return;

    const ok = confirm(`Xóa xe ${p} khỏi bãi?`);
    if (!ok) return;

    const form = new FormData();
    form.append('plate', p);

    const res = await postForm(API_BASE + '/active/delete', form);
    if (!res.ok) return;

    closeEditPlateModal();
    await loadActiveTable();
    await loadHistoryTable();
  }

  async function deleteHistoryByEventId(eventId) {
    const id = Number(eventId);
    if (!Number.isFinite(id)) return;

    const ok = confirm(`Xóa event_id=${id} khỏi lịch sử?`);
    if (!ok) return;

    const form = new FormData();
    form.append('event_id', String(id));

    const res = await postForm(API_BASE + '/history/delete', form);
    if (!res.ok) return;

    closeEditPlateModal();
    await loadActiveTable();
    await loadHistoryTable();
  }

  window.deleteActiveByPlate = deleteActiveByPlate;
  window.deleteHistoryByEventId = deleteHistoryByEventId;

  async function loadActiveTable() {
    try {
      const items = await fetchActiveItems();
      const tbody = document.getElementById('activeTbody');
      if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="muted">Hiện chưa có xe nào trong bãi.</td></tr>';
        return;
      }

      tbody.innerHTML = items.map(it => {
        return `
          <tr data-plate="${(it.plate || '').replace(/"/g, '')}" style="cursor:pointer;">
            <td><b>${it.plate || ''}</b></td>
            <td>${formatDateTime(it.time_in || '')}</td>
            <td>${it.spot_id || '-'}</td>
            <td>
              <div style="display:flex;gap:8px;">
                <button type="button" class="btn-secondary" style="width:auto;padding:8px 10px;" onclick="event.stopPropagation(); openEditPlateModalForActive(${JSON.stringify(it).replace(/</g,'\\u003c')})">Sửa</button>
                <button type="button" class="btn-danger" style="width:auto;padding:8px 10px;" onclick="event.stopPropagation(); deleteActiveByPlate('${(it.plate || '').replace(/'/g,"\\'")}')">Xóa</button>



              </div>
            </td>
          </tr>
        `;
      }).join('');

      // click to select
      tbody.querySelectorAll('tr').forEach(tr => {
        tr.addEventListener('click', () => {
          selectRow(tbody, tr);
          const plate = tr.getAttribute('data-plate');
          const it = items.find(x => x.plate === plate);
          if (it) {
            focusRowState = { section: 'active', plate: it.plate, event_id: null, spot_id: it.spot_id, time_in: it.time_in, time_out: null, status: 'IN' };
          }
        });
      });
    } catch (e) {
      document.getElementById('activeTbody').innerHTML = '<tr><td colspan="4" class="muted">Lỗi tải danh sách.</td></tr>';
    }
  }

  async function loadHistoryTable() {
    try {
      const res = await fetch(API_BASE + '/history');
      const json = await res.json();
      const items = json.items || [];
      const tbody = document.getElementById('historyTbody');

      if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="muted">Chưa có lịch sử.</td></tr>';
        return;
      }

      tbody.innerHTML = items.map(it => {
        const timeIn = it.time_in ? formatDateTime(it.time_in) : '-';
        const timeOut = it.time_out ? formatDateTime(it.time_out) : '-';
        const durationSec = it.duration_seconds;
        const hours = (durationSec === null || durationSec === undefined) ? '-' : hoursFromSeconds(durationSec);
        const fee = it.fee_vnd === null || it.fee_vnd === undefined ? '-' : `${Number(it.fee_vnd).toLocaleString('vi-VN')} VND`;

        return `
          <tr data-event-id="${it.event_id}" style="cursor:pointer;">
            <td><b>${it.plate || ''}</b></td>
            <td>${timeIn}</td>
            <td>${timeOut}</td>
            <td>${hours}</td>
            <td>${fee}</td>
            <td>
              <div style="display:flex;gap:8px;">
                <button type="button" class="btn-secondary" style="width:auto;padding:8px 10px;" onclick="event.stopPropagation(); openEditPlateModalForHistory(${JSON.stringify(it).replace(/</g,'\\u003c')})">Sửa</button>
                <button type="button" class="btn-danger" style="width:auto;padding:8px 10px;" onclick="event.stopPropagation(); deleteHistoryByEventId('${it.event_id}')">Xóa</button>
              </div>
            </td>
          </tr>

        `;
      }).join('');

      tbody.querySelectorAll('tr').forEach(tr => {
        tr.addEventListener('click', () => {
          selectRow(tbody, tr);
          const eventId = Number(tr.getAttribute('data-event-id'));
          const it = items.find(x => Number(x.event_id) === eventId);
          if (it) {
            focusRowState = {
              section: 'history',
              plate: it.plate,
              event_id: it.event_id,
              spot_id: it.spot_id,
              time_in: it.time_in,
              time_out: it.time_out,
              status: it.status,
            };
          }
        });
      });
    } catch (e) {
      document.getElementById('historyTbody').innerHTML = '<tr><td colspan="6" class="muted">Lỗi tải lịch sử.</td></tr>';
    }
  }


  // Initial state
  loadActiveTable();
  loadHistoryTable();
