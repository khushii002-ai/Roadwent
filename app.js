/* RoadRent front-end. Each page has <main data-page="..."> and runs its own init function. */
let R = document; // root element of the current page
const $ = (s, r = R) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const rs = n => "Rs " + Number(n).toLocaleString("en-IN");
const ICON = { Hatchback: "🚗", Sedan: "🚘", SUV: "🚙", Van: "🚐" };
const iso = d => d.toISOString().slice(0, 10);
const Q = () => new URLSearchParams(window.__vq ?? location.search);
const goto = url => (window.__goto ? window.__goto(url) : (location.href = url));

function toast(msg, err = false) {
  const t = document.getElementById("toast"); t.textContent = msg; t.className = "show" + (err ? " err" : "");
  clearTimeout(toast.t); toast.t = setTimeout(() => (t.className = ""), 3200);
}
async function api(url, method = "GET", body) {
  const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json();
  if (res.status === 401 && R.dataset?.page !== "login" && !url.startsWith("/api/login")) goto("/login?next=" + encodeURIComponent(window.__vpath ?? location.pathname + location.search));
  if (!res.ok) { const e = new Error(data.error || "Something went wrong."); e.status = res.status; throw e; }
  return data;
}
function setDates(a, b) {
  const q = Q();
  a.min = b.min = iso(new Date());
  a.value = q.get("start") || iso(new Date());
  b.value = q.get("end") || iso(new Date(Date.now() + 864e5));
}
function quote(price, start, end) {
  const days = Math.round((new Date(end) - new Date(start)) / 864e5) + 1;
  const disc = days >= 7 ? 10 : days >= 3 ? 5 : 0;
  return { days, disc, total: Math.round(days * price * (100 - disc) / 100) };
}
async function showStats() {
  const s = await api("/api/stats");
  $("#stats").innerHTML = [["Cars in fleet", s.cars], ["Trips booked", s.trips], ["Trips on the road or upcoming", s.active], ["Revenue", rs(s.revenue)]]
    .map(([l, n]) => `<div><b>${n}</b><span>${l}</span></div>`).join("");
}
function carCard(c, start, end) {
  const off = c.available === false;
  return `<article class="car ${off ? "off" : ""}">
    <div class="pic" aria-hidden="true">${ICON[c.type] || "🚗"}</div>
    <div class="body"><h3>${esc(c.name)}</h3>
      <span class="spec">${esc(c.type)} &middot; ${c.seats} seats &middot; ${esc(c.transmission)} &middot; ${esc(c.fuel)}</span>
      <span class="price">${rs(c.price_per_day)} <small>per day</small></span>
      ${off ? '<span class="tag no">Booked for these dates</span>' : '<span class="tag">Available</span>'}
      <a class="primary" ${off ? 'aria-disabled="true"' : ""} href="/book?car=${c.id}&start=${start}&end=${end}">Book this car</a>
    </div></article>`;
}
function bookingRow(b, admin) {
  const upcoming = b.status === "confirmed" && b.start_date > iso(new Date());
  return `<article class="row-card ${b.status}">
    <div class="info"><strong>${esc(b.car_name)}</strong> &middot; ${esc(b.ref)}
      <small>${esc(b.start_date)} to ${esc(b.end_date)} (${b.days} days) &middot; ${rs(b.total)}${admin ? ` &middot; ${esc(b.customer)}, ${esc(b.phone)}` : ""}</small></div>
    <span class="tag ${b.status === "cancelled" ? "no" : ""}">${esc(b.status)}</span>
    ${upcoming ? `<button class="small" data-cancel="${b.id}" data-phone="${esc(b.phone)}">Cancel</button>` : ""}</article>`;
}
function wireCancel(list, reload) {
  list.addEventListener("click", async e => {
    if (!e.target.dataset.cancel || !confirm("Cancel this booking?")) return;
    try { await api(`/api/bookings/${e.target.dataset.cancel}/cancel`, "POST", { phone: e.target.dataset.phone }); toast("Booking cancelled."); reload(); }
    catch (err) { toast(err.message, true); }
  });
}

const pages = {
  async home() {
    setDates($("#q-start"), $("#q-end"));
    $("#quick").addEventListener("submit", e => { e.preventDefault(); goto(`/cars?start=${$("#q-start").value}&end=${$("#q-end").value}&type=${$("#q-type").value}`); });
    showStats();
    const cars = await api("/api/cars");
    const pick = ["Hatchback", "Sedan", "SUV"].map(t => cars.find(c => c.type === t)).filter(Boolean);
    const s = iso(new Date()), e = iso(new Date(Date.now() + 864e5));
    $("#featured").innerHTML = pick.map(c => carCard(c, s, e)).join("");
  },

  cars() {
    setDates($("#start"), $("#end"));
    if (Q().get("type")) $("#type").value = Q().get("type");
    const load = async () => {
      const p = new URLSearchParams({ type: $("#type").value, seats: $("#seats").value, max_price: $("#maxp").value, start: $("#start").value, end: $("#end").value });
      try {
        const cars = await api("/api/cars?" + p);
        $("#cars").innerHTML = cars.length ? cars.map(c => carCard(c, $("#start").value, $("#end").value)).join("")
          : '<div class="empty">No cars match these filters. Try a higher price or fewer seats.</div>';
      } catch (e) { $("#cars").innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
    };
    ["start", "end", "type", "seats", "maxp"].forEach(id => $("#" + id).addEventListener("change", load));
    load();
  },

  async book() {
    const id = Q().get("car");
    let car;
    try { car = await api("/api/cars/" + id); }
    catch (e) { if (e.status !== 401) { $("#car-sum").innerHTML = 'Car not found. <a href="/cars">Choose a car</a>'; $("#book-form").hidden = true; } return; }
    const me = (await api("/api/me")).user;
    $("#as").textContent = `Booking as ${me.name} (${me.phone})`;
    $("#car-sum").innerHTML = `<strong>${ICON[car.type] || "🚗"} ${esc(car.name)}</strong><span class="spec">${esc(car.type)} &middot; ${car.seats} seats &middot; ${esc(car.transmission)} &middot; ${esc(car.fuel)} &middot; ${rs(car.price_per_day)} per day</span>`;
    setDates($("#b-start"), $("#b-end"));
    const update = async () => {
      const [s, e] = [$("#b-start").value, $("#b-end").value];
      const q = quote(car.price_per_day, s, e), btn = $("#confirm");
      if (!(q.days >= 1 && q.days <= 30)) { $("#quote").textContent = "Return date must be after pick-up (max 30 days)."; btn.disabled = true; return; }
      let free = true;
      try { free = (await api(`/api/cars?start=${s}&end=${e}`)).find(c => c.id == car.id).available; } catch { }
      $("#quote").textContent = free ? `${q.days} day${q.days > 1 ? "s" : ""}${q.disc ? `, ${q.disc}% discount` : ""}: total ${rs(q.total)}` : "This car is already booked for these dates. Pick other dates.";
      btn.disabled = !free;
    };
    ["b-start", "b-end"].forEach(i => $("#" + i).addEventListener("change", update));
    update();
    $("#book-form").addEventListener("submit", async ev => {
      ev.preventDefault();
      try {
        const r = await api("/api/bookings", "POST", { car_id: car.id, start: $("#b-start").value, end: $("#b-end").value });
        goto("/confirmation?ref=" + r.ref);
      } catch (err) { toast(err.message, true); update(); }
    });
  },

  async confirmation() {
    try {
      const b = await api("/api/bookings/" + encodeURIComponent(Q().get("ref") || ""));
      $("#ticket").innerHTML = `<div class="ticket"><p>Booking confirmed</p><div class="ref">${esc(b.ref)}</div>
        <dl><dt>Car</dt><dd>${esc(b.car_name)} (${esc(b.car_type)})</dd><dt>Pick-up</dt><dd>${esc(b.start_date)}</dd><dt>Return</dt><dd>${esc(b.end_date)} (${b.days} days)</dd>
        <dt>Customer</dt><dd>${esc(b.customer)}, ${esc(b.phone)}</dd><dt>Discount</dt><dd>${b.discount}%</dd><dt>Total to pay at pick-up</dt><dd>${rs(b.total)}</dd></dl>
        <p>Carry your driving licence and this reference when you collect the car.</p>
        <p class="noprint"><button class="small" id="print">Print ticket</button> <a class="small-link" href="/my-bookings">My bookings</a> <a class="small-link" href="/cars">Book another car</a></p></div>`;
      $("#print").addEventListener("click", () => window.print());
    } catch (e) { $("#ticket").innerHTML = `<div class="empty">${esc(e.message)} <a href="/cars">Choose a car</a></div>`; }
  },

  async mine() {
    const load = async () => {
      try {
        const rows = await api("/api/bookings");
        $("#my-list").innerHTML = rows.length ? rows.map(b => bookingRow(b, false)).join("") : '<div class="empty">No bookings yet. <a href="/cars">Find a car</a></div>';
      } catch { }
    };
    wireCancel($("#my-list"), load);
    load();
  },

  login() {
    $("#login-form").addEventListener("submit", async e => {
      e.preventDefault();
      try {
        const r = await api("/api/login", "POST", Object.fromEntries(new FormData(e.target)));
        const next = Q().get("next");
        goto(next && next.startsWith("/") && !next.startsWith("//") ? next : r.role === "admin" ? "/admin" : "/cars");
      } catch (err) { toast(err.message, true); }
    });
  },

  register() {
    $("#register-form").addEventListener("submit", async e => {
      e.preventDefault();
      try { await api("/api/register", "POST", Object.fromEntries(new FormData(e.target))); goto("/cars"); }
      catch (err) { toast(err.message, true); }
    });
  },

  async admin() {
    const load = async () => {
      try {
        const rows = await api("/api/admin/bookings");
        $("#admin-list").innerHTML = rows.length ? rows.map(b => bookingRow(b, true)).join("") : '<div class="empty">No bookings yet.</div>';
        showStats();
      } catch (e) { if (e.status === 403) goto("/"); }
    };
    wireCancel($("#admin-list"), load);
    load();
  },

  async fleet() {
    const load = async () => {
      try {
        const cars = await api("/api/cars");
        $("#fleet-list").innerHTML = cars.map(c => `<article class="row-card"><div class="info"><strong>${esc(c.name)}</strong>
          <small>${esc(c.type)} &middot; ${c.seats} seats &middot; ${esc(c.transmission)} &middot; ${esc(c.fuel)}</small></div><span class="price">${rs(c.price_per_day)}</span></article>`).join("");
      } catch { }
    };
    $("#car-form").addEventListener("submit", async e => {
      e.preventDefault();
      try { await api("/api/admin/cars", "POST", Object.fromEntries(new FormData(e.target))); e.target.reset(); toast("Car added to the fleet."); load(); }
      catch (err) { toast(err.message, true); }
    });
    load();
  },
};

const mainEl = document.querySelector("main[data-page]");
if (mainEl && !window.__preview) { R = mainEl; pages[mainEl.dataset.page]?.(); }
