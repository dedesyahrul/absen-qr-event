<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Bell, CalendarDays, Camera, CameraOff, Check, ChevronDown, CircleAlert, CircleCheck, Download, Eye, LayoutDashboard, LogOut, Plus, QrCode, RefreshCw, Search, Settings, ShieldCheck, Sparkles, UserRound, Users, X } from '@lucide/vue'
import QrScanner from 'qr-scanner'

const API = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:18081/api`
const token = ref(localStorage.getItem('gatherly_token') || '')
const user = ref(JSON.parse(localStorage.getItem('gatherly_user') || 'null'))
const loading = ref(false)
const loginError = ref('')
const loginForm = ref({ email: 'admin@example.com', password: 'admin123' })
const activeView = ref('overview')
const event = ref(null)
const dashboard = ref(null)
const participants = ref([])
const vendors = ref([])
const search = ref('')
const scanToken = ref('')
const scanMessage = ref(null)
const showParticipantForm = ref(false)
const participantForm = ref({ name: '', position: '', phone: '', email: '', vendor_id: null })

// QR Code viewer state
const showQrModal = ref(false)
const qrParticipant = ref(null)
const qrImageUrl = ref('')
const qrLoading = ref(false)

// Camera scanner state
const cameraActive = ref(false)
const videoEl = ref(null)
let qrScannerInstance = null

const headers = () => ({ 'Content-Type': 'application/json', ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}) })
async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, { ...options, headers: { ...headers(), ...(options.headers || {}) } })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || 'Terjadi kesalahan pada server')
  return body
}
async function login() {
  loading.value = true; loginError.value = ''
  try {
    const result = await api('/auth/login', { method: 'POST', body: JSON.stringify(loginForm.value) })
    token.value = result.access_token; user.value = result.user
    localStorage.setItem('gatherly_token', token.value); localStorage.setItem('gatherly_user', JSON.stringify(user.value))
    await loadData()
  } catch (error) { loginError.value = error.message } finally { loading.value = false }
}
function logout() { token.value = ''; user.value = null; localStorage.removeItem('gatherly_token'); localStorage.removeItem('gatherly_user') }
async function loadData() {
  loading.value = true
  try {
    const events = await api('/events')
    event.value = events[0]
    if (!event.value) return
    await refreshEventData()
  } catch (error) {
    if (error.message.includes('token') || error.message.includes('Authentication')) logout()
  } finally { loading.value = false }
}
async function refreshEventData() {
  if (!event.value) return
  const [dash, people, vendorList] = await Promise.all([api(`/events/${event.value.id}/dashboard`), api(`/events/${event.value.id}/participants?search=${encodeURIComponent(search.value)}`), api(`/events/${event.value.id}/vendors`)])
  dashboard.value = dash; participants.value = people; vendors.value = vendorList
}
async function refreshSearch() { if (event.value) participants.value = await api(`/events/${event.value.id}/participants?search=${encodeURIComponent(search.value)}`) }
async function checkIn(mode = 'qr', participantId = null) {
  if (!event.value) return
  try {
    const payload = mode === 'qr' ? { token: scanToken.value.trim() } : { participant_id: participantId, notes: 'Verified at registration desk' }
    const result = await api(`/events/${event.value.id}/attendance/${mode === 'qr' ? 'scan' : 'manual'}`, { method: 'POST', body: JSON.stringify(payload) })
    scanMessage.value = { type: result.result === 'already_checked_in' ? 'warning' : 'success', title: result.result === 'already_checked_in' ? 'Peserta sudah check-in' : 'Check-in berhasil', text: `${result.participant.name} • ${result.participant.company_name}` }
    scanToken.value = ''; await refreshEventData()
  } catch (error) { scanMessage.value = { type: 'error', title: 'Scan tidak berhasil', text: error.message } }
}
async function addParticipant() {
  if (!participantForm.value.name.trim()) return
  await api(`/events/${event.value.id}/participants`, { method: 'POST', body: JSON.stringify(participantForm.value) })
  participantForm.value = { name: '', position: '', phone: '', email: '', vendor_id: null }; showParticipantForm.value = false; await refreshEventData()
}
function focusScanner() { activeView.value = 'scanner'; nextTick(() => document.querySelector('#scan-input')?.focus()) }

// QR Code functions
async function showQr(person) {
  qrParticipant.value = person
  qrLoading.value = true
  showQrModal.value = true
  try {
    const response = await fetch(`${API}/events/${event.value.id}/participants/${person.id}/qr`, { headers: { Authorization: `Bearer ${token.value}` } })
    if (!response.ok) throw new Error('Gagal memuat QR Code')
    const blob = await response.blob()
    qrImageUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    scanMessage.value = { type: 'error', title: 'Error', text: error.message }
    showQrModal.value = false
  } finally { qrLoading.value = false }
}
function closeQrModal() {
  showQrModal.value = false
  if (qrImageUrl.value) { URL.revokeObjectURL(qrImageUrl.value); qrImageUrl.value = '' }
  qrParticipant.value = null
}
function downloadQr() {
  if (!qrImageUrl.value || !qrParticipant.value) return
  const link = document.createElement('a')
  link.href = qrImageUrl.value
  link.download = `qr_${qrParticipant.value.name.replace(/\s+/g, '_')}_${qrParticipant.value.id}.png`
  link.click()
}
async function downloadAllQr() {
  if (!event.value) return
  try {
    const response = await fetch(`${API}/events/${event.value.id}/participants/qr-all`, { headers: { Authorization: `Bearer ${token.value}` } })
    if (!response.ok) throw new Error('Gagal mengunduh QR Code')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `qr_codes_${event.value.name.replace(/\s+/g, '_')}.zip`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) { scanMessage.value = { type: 'error', title: 'Error', text: error.message } }
}

// Camera scanner functions
async function startCamera() {
  if (!videoEl.value) return
  try {
    qrScannerInstance = new QrScanner(videoEl.value, result => {
      const scannedToken = result.data.trim()
      if (scannedToken) {
        scanToken.value = scannedToken
        stopCamera()
        checkIn('qr')
      }
    }, { returnDetailedScanResult: true, highlightScanRegion: true, highlightCodeOutline: true })
    await qrScannerInstance.start()
    cameraActive.value = true
  } catch (error) {
    scanMessage.value = { type: 'error', title: 'Kamera tidak tersedia', text: error.message || 'Pastikan izin kamera diberikan.' }
    cameraActive.value = false
  }
}
function stopCamera() {
  if (qrScannerInstance) { qrScannerInstance.stop(); qrScannerInstance.destroy(); qrScannerInstance = null }
  cameraActive.value = false
}
function toggleCamera() { cameraActive.value ? stopCamera() : startCamera() }

// Cleanup camera on view change or unmount
watch(activeView, (newView) => { if (newView !== 'scanner') stopCamera() })
onUnmounted(() => stopCamera())

const checkedIn = computed(() => dashboard.value?.summary?.checked_in || 0)
const total = computed(() => dashboard.value?.summary?.total || 0)
const lastCheckins = computed(() => dashboard.value?.recent || [])
onMounted(() => { if (token.value) loadData() })
</script>

<template>
  <div v-if="!token" class="login-page">
    <div class="login-art"><div class="art-orbit orbit-one"></div><div class="art-orbit orbit-two"></div><div class="art-content"><div class="brand large"><span class="brand-mark"><QrCode :size="21" /></span>gatherly<span class="brand-dot">.</span></div><p class="art-kicker">EVENT OPERATIONS, REIMAGINED</p><h1>Make every arrival<br /><em>feel effortless.</em></h1><p class="art-description">A calm, intelligent command center for your most important gatherings.</p><div class="art-stat"><ShieldCheck :size="18" /><span>Trusted attendance records<br /><b>Secure by design</b></span></div></div></div>
    <div class="login-panel"><div class="login-inner"><div class="mobile-logo brand">gatherly<span class="brand-dot">.</span></div><p class="eyebrow">Welcome back</p><h2>Sign in to your workspace</h2><p class="login-subtitle">Manage your event, vendors, and attendance in one place.</p><form @submit.prevent="login"><label>Email address<input v-model="loginForm.email" type="email" placeholder="you@company.com" /></label><label>Password<div class="password-input"><input v-model="loginForm.password" type="password" placeholder="Your password" /><ShieldCheck :size="16" /></div></label><div v-if="loginError" class="form-error"><CircleAlert :size="15" />{{ loginError }}</div><button class="primary-button full" :disabled="loading">{{ loading ? 'Signing in...' : 'Continue to workspace' }} <span>→</span></button></form><p class="login-hint">Development access: <b>admin@example.com</b> / <b>admin123</b></p></div><span class="copyright">© 2026 Gatherly. Built for better events.</span></div>
  </div>

  <div v-else class="app-shell">
    <aside class="sidebar"><div class="brand"><span class="brand-mark"><QrCode :size="20" /></span>gatherly<span class="brand-dot">.</span></div><p class="eyebrow">Workspace</p><nav><button :class="['nav-item', { active: activeView === 'overview' }]" @click="activeView = 'overview'"><LayoutDashboard :size="18" />Overview</button><button :class="['nav-item', { active: activeView === 'scanner' }]" @click="focusScanner"><QrCode :size="18" />Scan attendance<span class="nav-badge">LIVE</span></button><button :class="['nav-item', { active: activeView === 'participants' }]" @click="activeView = 'participants'"><Users :size="18" />Participants</button><button :class="['nav-item', { active: activeView === 'vendors' }]" @click="activeView = 'vendors'"><UserRound :size="18" />Vendors</button><button class="nav-item" @click="refreshEventData"><Settings :size="18" />Refresh data</button></nav><div v-if="event" class="sidebar-event"><div class="event-icon"><CalendarDays :size="18" /></div><div><small>Current event</small><strong>{{ event.name }}</strong><span>{{ event.event_date }} · {{ event.location }}</span></div></div><div class="user-card"><div class="avatar">{{ user?.name?.slice(0, 2).toUpperCase() }}</div><div><strong>{{ user?.name }}</strong><span>{{ user?.role }}</span></div><button @click="logout" title="Sign out"><LogOut :size="15" /></button></div></aside>
    <main class="main-content"><header class="topbar"><div class="mobile-brand brand">gatherly<span class="brand-dot">.</span></div><div class="top-actions"><span class="live-indicator"><i></i> System online</span><button class="icon-button"><Bell :size="19" /></button><div class="top-avatar">{{ user?.name?.slice(0, 2).toUpperCase() }}</div></div></header>
      <section class="content"><div class="heading-row"><div><p class="eyebrow">{{ event?.event_date }} · Event command center</p><h1>{{ activeView === 'overview' ? `Good morning, ${user?.name?.split(' ')[0]}` : activeView === 'scanner' ? 'Attendance scanner' : activeView === 'participants' ? 'Participants' : 'Vendor directory' }}<span class="wave">✦</span></h1><p class="subtitle">{{ activeView === 'overview' ? 'Here is what is happening at your event today.' : 'Everything you need to keep the room moving.' }}</p></div><button class="primary-button" @click="focusScanner"><QrCode :size="18" /> Open scanner</button></div>

        <template v-if="activeView === 'overview'">
          <div class="event-banner"><div class="banner-copy"><span class="live-pill"><span></span> {{ event?.status || 'Live' }} event</span><h2>{{ event?.name }}</h2><p>{{ event?.location }} <span>•</span> {{ event?.start_time }} – {{ event?.end_time }} WIB</p></div><div class="banner-date"><strong>{{ event?.event_date?.slice(8, 10) }}</strong><span>{{ event?.event_date?.slice(5, 7) }}</span></div></div>
          <div class="stats-grid"><article class="stat-card"><div class="stat-icon blue-icon"><Users :size="19" /></div><span>Total invitees</span><strong>{{ total }}</strong><small>Across {{ vendors.length }} companies</small></article><article class="stat-card"><div class="stat-icon green-icon"><CircleCheck :size="19" /></div><span>Checked in</span><strong>{{ checkedIn }}</strong><small class="positive">{{ dashboard?.summary?.rate || 0 }}% <em>attendance rate</em></small></article><article class="stat-card"><div class="stat-icon orange-icon"><QrCode :size="19" /></div><span>Remaining</span><strong>{{ dashboard?.summary?.remaining || 0 }}</strong><small>Ready for arrival</small></article><article class="stat-card accent-card"><span>System status</span><strong class="online-text">Live</strong><small>Updates on refresh</small><div class="progress"><span :style="{ width: `${dashboard?.summary?.rate || 0}%` }"></span></div></article></div>
          <div class="section-grid"><section class="panel chart-panel"><div class="panel-heading"><div><h3>Attendance progress</h3><p>Live snapshot of event arrivals</p></div><button class="select-button" @click="refreshEventData"><RefreshCw :size="13" /> Refresh</button></div><div class="big-progress"><div class="ring"><strong>{{ dashboard?.summary?.rate || 0 }}<small>%</small></strong><span>attended</span></div><div class="progress-copy"><strong>{{ checkedIn }} of {{ total }}</strong><span>participants have checked in</span><div class="bar large"><i :style="{ width: `${dashboard?.summary?.rate || 0}%` }"></i></div><small>Keep the welcome desk moving.</small></div></div></section><section class="panel progress-panel"><div class="panel-heading"><div><h3>Vendor attendance</h3><p>Participation by company</p></div><button class="text-button" @click="activeView = 'vendors'">View all</button></div><div v-for="vendor in (dashboard?.vendors || []).slice(0, 5)" :key="vendor.id" class="vendor-row"><div class="vendor-meta"><span>{{ String(vendor.id).padStart(2, '0') }}</span><strong>{{ vendor.company_name }}</strong><b>{{ vendor.checked_in }} / {{ vendor.total }}</b></div><div class="bar"><i :style="{ width: `${vendor.rate}%` }"></i></div></div></section></div>
          <section class="panel activity-panel"><div class="panel-heading"><div><h3>Latest check-ins</h3><p>Real-time attendance activity</p></div><button class="text-button" @click="focusScanner">Scan next <span>→</span></button></div><div v-if="lastCheckins.length" class="table-wrap"><table><thead><tr><th>Attendee</th><th>Company</th><th>Check-in time</th><th>Status</th></tr></thead><tbody><tr v-for="person in lastCheckins" :key="person.id"><td><div class="person"><span class="person-avatar coral">{{ person.name.slice(0, 2).toUpperCase() }}</span><strong>{{ person.name }}</strong></div></td><td>{{ person.company_name }}</td><td>{{ new Date(person.check_in_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) }} WIB</td><td><span class="status"><i></i>Checked in</span></td></tr></tbody></table></div><div v-else class="empty-state"><Sparkles :size="24" /><strong>No check-ins yet</strong><span>Scanned participants will appear here.</span></div></section>
        </template>

        <template v-else-if="activeView === 'scanner'"><section class="scanner-layout"><div class="panel scanner-panel"><div class="scanner-head"><div><span class="live-pill dark"><span></span> Scanner ready</span><h2>Scan a participant QR</h2><p>Point the camera at a QR Code or enter its token below.</p></div><div class="scanner-icon"><QrCode :size="35" /></div></div><div class="camera-container"><video ref="videoEl" class="camera-video" :class="{ active: cameraActive }"></video><div v-if="!cameraActive" class="camera-placeholder" @click="toggleCamera"><div class="scan-corners"></div><Camera :size="52" /><span>Tap to activate camera scanner</span><small>Or use the token field below</small></div></div><div class="camera-controls"><button :class="['camera-toggle', { active: cameraActive }]" @click="toggleCamera"><Camera v-if="!cameraActive" :size="17" /><CameraOff v-else :size="17" /> {{ cameraActive ? 'Stop camera' : 'Start camera' }}</button></div><div class="scan-form"><label id="scan-input">QR token<input v-model="scanToken" @keyup.enter="checkIn('qr')" placeholder="Paste or type participant token" autofocus /></label><button class="primary-button" @click="checkIn('qr')" :disabled="!scanToken.trim()"><Check :size="17" /> Confirm check-in</button></div><div v-if="scanMessage" :class="['scan-result', scanMessage.type]"><CircleCheck v-if="scanMessage.type === 'success'" :size="22" /><CircleAlert v-else :size="22" /><div><strong>{{ scanMessage.title }}</strong><span>{{ scanMessage.text }}</span></div><button @click="scanMessage = null"><X :size="16" /></button></div></div><div class="panel quick-panel"><h3>Quick manual check-in</h3><p>Use this fallback when a guest cannot show their QR Code.</p><div class="search-field"><Search :size="16" /><input v-model="search" @input="refreshSearch" placeholder="Find a participant" /></div><div class="quick-list"><div v-for="person in participants.slice(0, 5)" :key="person.id" class="quick-person"><div class="person"><span class="person-avatar blue">{{ person.name.slice(0, 2).toUpperCase() }}</span><div><strong>{{ person.name }}</strong><small>{{ person.company_name }}</small></div></div><button v-if="person.attendance_status !== 'checked_in'" class="tiny-button" @click="checkIn('manual', person.id)">Check in</button><span v-else class="already">Done</span></div></div></div></section></template>

        <template v-else-if="activeView === 'participants'"><section class="panel activity-panel"><div class="panel-heading"><div><h3>All participants</h3><p>{{ participants.length }} records in this event</p></div><div class="panel-actions"><button class="select-button" @click="downloadAllQr"><Download :size="15" /> Download all QR</button><button class="primary-button small" @click="showParticipantForm = true"><Plus :size="16" /> Add participant</button></div></div><div class="toolbar"><div class="search-field"><Search :size="16" /><input v-model="search" @input="refreshSearch" placeholder="Search name, phone, or email..." /></div><button class="select-button" @click="refreshEventData"><RefreshCw :size="13" /> Refresh</button></div><div class="table-wrap"><table><thead><tr><th>Participant</th><th>Company</th><th>Contact</th><th>QR Code</th><th>Status</th><th>Action</th></tr></thead><tbody><tr v-for="person in participants" :key="person.id"><td><div class="person"><span class="person-avatar coral">{{ person.name.slice(0, 2).toUpperCase() }}</span><strong>{{ person.name }}</strong></div></td><td>{{ person.company_name }}</td><td>{{ person.phone || person.email || '—' }}</td><td><button class="qr-button" @click="showQr(person)" title="Lihat QR Code"><Eye :size="14" /> <span>QR</span></button></td><td><span :class="['status', person.attendance_status === 'checked_in' ? '' : 'pending']"><i></i>{{ person.attendance_status === 'checked_in' ? 'Checked in' : 'Not arrived' }}</span></td><td><button v-if="person.attendance_status !== 'checked_in'" class="tiny-button" @click="checkIn('manual', person.id)">Check in</button><span v-else class="muted">{{ new Date(person.check_in_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) }}</span></td></tr></tbody></table></div></section></template>

        <template v-else><section class="vendor-cards"><article v-for="vendor in vendors" :key="vendor.id" class="panel vendor-card"><div class="vendor-avatar"><Users :size="19" /></div><h3>{{ vendor.company_name }}</h3><span>{{ vendor.category }}</span><div class="vendor-count"><strong>{{ vendor.participant_count }}</strong><small>participants</small></div><div class="bar"><i :style="{ width: `${dashboard?.vendors?.find(v => v.id === vendor.id)?.rate || 0}%` }"></i></div></article></section></template>
      </section>
    </main>
    <div v-if="showParticipantForm" class="modal-backdrop" @click.self="showParticipantForm = false"><form class="modal" @submit.prevent="addParticipant"><button type="button" class="modal-close" @click="showParticipantForm = false"><X :size="18" /></button><p class="eyebrow">New registration</p><h2>Add participant</h2><p class="subtitle">Create a QR token automatically for this guest.</p><label>Full name<input v-model="participantForm.name" required placeholder="e.g. Raka Pratama" /></label><label>Company<select v-model="participantForm.vendor_id"><option :value="null">Select company</option><option v-for="vendor in vendors" :key="vendor.id" :value="vendor.id">{{ vendor.company_name }}</option></select></label><label>Position<input v-model="participantForm.position" placeholder="Vendor representative" /></label><label>Phone<input v-model="participantForm.phone" placeholder="08xx" /></label><button class="primary-button full" type="submit"><Plus :size="17" /> Create participant</button></form></div>
    <div v-if="showQrModal" class="modal-backdrop" @click.self="closeQrModal"><div class="modal qr-modal"><button type="button" class="modal-close" @click="closeQrModal"><X :size="18" /></button><p class="eyebrow">QR Code</p><h2>{{ qrParticipant?.name }}</h2><p class="subtitle">{{ qrParticipant?.company_name }} &bull; Token: <code>{{ qrParticipant?.qr_token?.slice(0, 12) }}...</code></p><div class="qr-preview"><div v-if="qrLoading" class="qr-loading"><RefreshCw :size="28" class="spin" /><span>Generating QR Code...</span></div><img v-else-if="qrImageUrl" :src="qrImageUrl" :alt="`QR Code ${qrParticipant?.name}`" /></div><div class="qr-actions"><button class="primary-button" @click="downloadQr"><Download :size="17" /> Download PNG</button><button class="select-button" @click="closeQrModal">Tutup</button></div></div></div>
  </div>
</template>
