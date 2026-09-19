(() => {
  'use strict';
  let snapshot = null;
  let busy = false;
  let connectionError = false;
  const $ = id => document.getElementById(id);
  const title = text => text.charAt(0).toUpperCase() + text.slice(1);
  const gib = bytes => Number.isFinite(bytes) ? (bytes / 2 ** 30).toLocaleString(undefined, {maximumFractionDigits: 1}) : '—';
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const pill = (text, state = '') => element('span', text, `pill ${state}`);
  const hostState = host => {
    if (!host) return 'loading';
    if (connectionError) return host.observed_at ? 'stale' : 'unavailable';
    if (host.observed_at && Date.now() - Date.parse(host.observed_at) > (snapshot?.stale_seconds || 90) * 1000) return 'stale';
    return host.state;
  };
  const guests = () => (snapshot?.hosts || []).flatMap(host => host.guests.map(guest => ({...guest, freshness: hostState(host)})));

  function switchView() {
    const fleet = location.hash === '#fleet';
    $('services-view').hidden = fleet;
    $('fleet-view').hidden = !fleet;
    document.querySelectorAll('.view-nav a').forEach(link => {
      if ((link.hash === '#fleet') === fleet) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  }

  function focusGuest(key) {
    const [host, type, id] = key.split(':');
    $('fleet-host').value = host;
    $('fleet-kind').value = type;
    $('fleet-state').value = 'all';
    $('fleet-search').value = id;
    location.hash = 'fleet';
    switchView();
    renderTable();
    $('fleet-heading').scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  function renderHosts() {
    const container = $('host-summary');
    container.replaceChildren();
    const hosts = snapshot?.hosts || ['sefer', 'seykhl'].map(host => ({host, guests: [], state: 'loading'}));
    for (const host of hosts) {
      const state = hostState(host);
      const card = element('article', undefined, 'host-card');
      const heading = element('div', undefined, 'host-heading');
      heading.append(element('h2', title(host.host)), pill({ok: 'Connected', loading: 'Connecting', stale: 'Stale', unavailable: 'Unavailable'}[state] || state, state));
      card.append(heading);
      const numbers = element('div', undefined, 'host-numbers');
      for (const [kind, label] of [['qemu', 'running VMs'], ['lxc', 'running containers']]) {
        const block = element('div');
        const count = host.observed_at ? host.guests.filter(g => g.type === kind && g.status === 'running').length : '—';
        block.append(element('strong', count), element('span', label));
        numbers.append(block);
      }
      card.append(numbers);
      if (host.observed_at) {
        card.append(element('p', `CPU ${Number.isFinite(host.cpu) ? (host.cpu * 100).toFixed(0) + '%' : '—'} · RAM ${gib(host.memory?.used)} / ${gib(host.memory?.total)} GiB`, 'host-detail'));
        const primary = host.storage?.find(s => s.storage === (host.host === 'sefer' ? 'vmdata' : 'local-lvm'));
        if (primary) card.append(element('p', `${primary.storage}: ${gib(primary.avail)} GiB available`, 'host-detail'));
        card.append(element('p', `Observed ${new Date(host.observed_at).toLocaleString()}${state === 'stale' ? ' · retained reading' : ''}`, 'host-detail'));
      } else card.append(element('p', state === 'loading' ? 'Waiting for the first inventory…' : 'No inventory received. Counts are unknown.', 'host-detail'));
      container.append(card);
    }
    const problems = hosts.filter(host => !['ok', 'loading'].includes(hostState(host)));
    $('fleet-warning').hidden = problems.length === 0 && !connectionError;
    $('fleet-warning').textContent = connectionError
      ? 'The dashboard could not refresh. Retained readings are marked stale; they do not confirm current VM state.'
      : problems.map(host => `${title(host.host)} inventory is ${hostState(host)}. ${host.observed_at ? 'Showing its last successful reading.' : 'Its guests are not yet included.'}`).join(' ');
    const times = hosts.filter(h => h.observed_at).map(h => Date.parse(h.observed_at));
    $('timestamp').textContent = times.length ? `Inventory observed ${new Date(Math.min(...times)).toLocaleString()} · refreshes every 30 seconds` : 'Connecting to Sefer and Seykhl…';
  }

  function renderPlacements() {
    const current = new Map(guests().map(guest => [guest.key, guest]));
    document.querySelectorAll('.service[data-guest], .service[data-host]').forEach(service => {
      let placement = service.querySelector('.placement');
      if (!placement) {
        placement = element('div', undefined, 'placement');
        service.querySelector('.service-name').after(placement);
      }
      placement.replaceChildren();
      const key = service.dataset.guest;
      const host = key ? key.split(':')[0] : service.dataset.host;
      const hostData = snapshot?.hosts.find(h => h.host === host);
      const state = hostState(hostData);
      const locationLink = element('a', title(host), host);
      locationLink.href = '#fleet';
      locationLink.addEventListener('click', event => {
        event.preventDefault();
        if (key) focusGuest(key);
        else {
          $('fleet-host').value = host; $('fleet-search').value = ''; $('fleet-state').value = 'running';
          location.hash = 'fleet'; switchView(); renderTable();
        }
      });
      placement.append(locationLink);
      let label, status;
      if (key) {
        placement.append(element('span', `${key.split(':')[1] === 'qemu' ? 'VM' : 'CT'} ${key.split(':')[2]}`));
        const guest = current.get(key);
        const matches = guest && (!service.dataset.guestName || guest.name === service.dataset.guestName);
        if (state !== 'ok') { label = state === 'loading' ? 'Checking VM' : 'State unverified'; status = state; }
        else if (!guest) { label = 'Not in inventory'; status = 'unavailable'; }
        else if (!matches) { label = 'Placement needs review'; status = 'unavailable'; }
        else { label = `VM ${guest.status}`; status = guest.status; }
      } else { label = state === 'ok' ? 'Host connected' : title(state); status = state; }
      placement.append(element('span', label, `guest-state ${status}`));
      const indicator = service.querySelector('.status-indicator');
      if (indicator) {
        indicator.className = `status-indicator ${status === 'running' || status === 'ok' ? 'status-active' : status === 'stale' ? 'status-stale' : 'status-unknown'}`;
        indicator.title = label;
      }
    });
  }

  function renderTable() {
    const body = $('fleet-body');
    const query = $('fleet-search').value.toLowerCase().trim();
    const host = $('fleet-host').value, kind = $('fleet-kind').value, state = $('fleet-state').value;
    const rows = guests().filter(g => (host === 'all' || g.host === host) && (kind === 'all' || g.type === kind) &&
      (state === 'all' || g.status === state) && (!query || [g.name, g.vmid, g.host, ...g.services, ...g.tags, ...g.storage].join(' ').toLowerCase().includes(query)))
      .sort((a, b) => a.host.localeCompare(b.host) || a.vmid - b.vmid || a.type.localeCompare(b.type));
    body.replaceChildren();
    for (const guest of rows) {
      const row = element('tr'); row.dataset.key = guest.key;
      const hostCell = element('td'); hostCell.append(pill(title(guest.host), guest.host));
      const idCell = element('td', `${guest.type === 'qemu' ? 'VM' : 'CT'} ${guest.vmid}`);
      const name = element('td', guest.name, 'guest-name');
      if (guest.tags.length) name.append(element('div', guest.tags.join(' · '), 'guest-subline'));
      const status = element('td'); status.append(pill(title(guest.status), guest.freshness === 'ok' ? guest.status : 'stale'));
      if (guest.freshness !== 'ok') status.append(element('div', 'Last known · stale', 'guest-subline'));
      if (guest.lock) status.append(element('div', `Lock: ${guest.lock}`, 'guest-subline'));
      const services = element('td', undefined, 'guest-services');
      if (guest.services.length) guest.services.forEach(s => services.append(pill(s)));
      else services.append(element('span', 'Not catalogued', 'guest-subline'));
      const disk = element('td', gib(guest.disk_bytes), 'number');
      disk.append(element('div', guest.storage.join(', '), 'guest-subline'));
      row.append(hostCell, idCell, name, status, services, element('td', guest.cpus, 'number'), element('td', gib(guest.memory_bytes), 'number'), disk);
      body.append(row);
    }
    if (!rows.length) {
      const waiting = !snapshot || snapshot.hosts.some(h => hostState(h) === 'loading');
      const unavailable = snapshot && snapshot.hosts.every(h => !h.observed_at);
      const row = element('tr'), cell = element('td', waiting ? 'Waiting for host inventory…' : unavailable ? 'Host inventory is unavailable. Try refreshing shortly.' : 'No guests match these filters.', 'fleet-empty');
      cell.colSpan = 8; row.append(cell); body.append(row);
    }
    const label = kind === 'qemu' ? 'VMs' : kind === 'lxc' ? 'containers' : 'guests';
    const incomplete = snapshot?.hosts.some(h => hostState(h) !== 'ok');
    $('fleet-count').textContent = `${rows.length} ${label} shown${incomplete ? ' · incomplete or stale inventory' : ''}`;
  }

  async function refresh() {
    if (busy) return;
    busy = true; $('fleet-refresh').disabled = true;
    try {
      const response = await fetch('/_fleet.json', {cache: 'no-store', signal: AbortSignal.timeout(10000)});
      if (!response.ok) throw new Error('Inventory unavailable');
      const data = await response.json();
      if (!Array.isArray(data.hosts)) throw new Error('Invalid inventory');
      snapshot = data; connectionError = false;
    } catch (_) { connectionError = true; }
    finally {
      busy = false; $('fleet-refresh').disabled = false;
      renderHosts(); renderPlacements(); renderTable();
    }
  }

  ['fleet-host', 'fleet-kind', 'fleet-state'].forEach(id => $(id).addEventListener('change', renderTable));
  $('fleet-search').addEventListener('input', renderTable);
  $('fleet-refresh').addEventListener('click', refresh);
  window.addEventListener('hashchange', switchView);
  switchView(); renderHosts(); renderPlacements(); renderTable(); refresh();
  setInterval(refresh, 30000);
})();
