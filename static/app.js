// ==========================================
// GLOBALS & STATE MANAGEMENT
// ==========================================
let currentUser = {
    userId: localStorage.getItem('user_id'),
    username: localStorage.getItem('username') || 'Guest',
    role: localStorage.getItem('role') || 'Staff'
};

let activeView = 'dashboard';
let currentEditId = null;
let currentFamilies = [];
let currentEvacuees = [];
let currentRooms = [];
let currentInventory = [];
let currentUsers = [];

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ==========================================
// APP INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // Check authentication state
    checkAuth();
    
    // Set date header
    updateDateDisplay();
    
    // Initialize Theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    // Initialize Lucide icons
    lucide.createIcons();
});

function checkAuth() {
    if (currentUser.userId) {
        document.getElementById('login-container').classList.add('hidden');
        document.getElementById('app-container').classList.remove('hidden');
        
        // Update user display
        document.getElementById('display-username').textContent = currentUser.username;
        document.getElementById('display-role').textContent = currentUser.role;
        document.getElementById('user-avatar').textContent = currentUser.username.charAt(0).toUpperCase();
        
        // Hide/Show Admin features
        const adminElements = document.querySelectorAll('.admin-only');
        if (currentUser.role === 'Admin') {
            adminElements.forEach(el => el.classList.remove('hidden'));
        } else {
            adminElements.forEach(el => el.classList.add('hidden'));
        }
        
        // Fetch server IP and load initial view
        fetchServerInfo();
        navigateTo(activeView);
    } else {
        document.getElementById('login-container').classList.remove('hidden');
        document.getElementById('app-container').classList.add('hidden');
    }
}

function updateDateDisplay() {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('display-date').textContent = new Date().toLocaleDateString('en-US', options);
}

function copyPublicUrl(url) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => {
            showAlert('Permanent Public Gateway URL copied to clipboard!', true);
        }).catch(() => {
            prompt('Copy Permanent URL:', url);
        });
    } else {
        prompt('Copy Permanent URL:', url);
    }
}

// ==========================================
// PWA & SERVICE WORKER REGISTRATION (100% OFFLINE)
// ==========================================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js').then(() => {
            console.log('EvacuMate Offline Service Worker active');
        }).catch((err) => {
            console.log('ServiceWorker note:', err);
        });
    });
}

let currentServerData = null;

function openOfflineQrModal() {
    const modal = document.getElementById('offline-qr-modal');
    if (modal) modal.classList.remove('hidden');
    if (currentServerData) {
        const permEl = document.getElementById('qr-permanent-url');
        const ipEl = document.getElementById('qr-ip-url');
        if (permEl) permEl.textContent = currentServerData.offline_permanent_url || 'http://evacumate.local:8550';
        if (ipEl) ipEl.textContent = currentServerData.network_ip_url || `http://${currentServerData.ip}:8550`;
    }
    switchQrCode('mdns');
    if (window.lucide) lucide.createIcons();
}

function closeOfflineQrModal() {
    const modal = document.getElementById('offline-qr-modal');
    if (modal) modal.classList.add('hidden');
}

function switchQrCode(type) {
    const btnMdns = document.getElementById('btn-qr-mdns');
    const btnIp = document.getElementById('btn-qr-ip');
    const img = document.getElementById('qr-code-img');
    if (!img) return;

    if (type === 'ip') {
        if (btnIp) btnIp.classList.add('active');
        if (btnMdns) btnMdns.classList.remove('active');
        img.src = '/api/qr-code?target=ip&t=' + Date.now();
    } else {
        if (btnMdns) btnMdns.classList.add('active');
        if (btnIp) btnIp.classList.remove('active');
        img.src = '/api/qr-code?target=mdns&t=' + Date.now();
    }
}

function copyUrlFromElem(elemId) {
    const el = document.getElementById(elemId);
    if (el) {
        copyPublicUrl(el.textContent.trim());
    }
}

async function fetchServerInfo() {
    try {
        const res = await fetch('/api/server-info');
        const data = await res.json();
        currentServerData = data;
        const container = document.getElementById('web-access-ip');
        const offlineUrl = data.offline_permanent_url || 'http://evacumate.local:8550';
        
        if (data.public_url) {
            container.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:3px; width:100%; text-align:center;">
                    <div style="display:flex; align-items:center; justify-content:center; gap:6px;">
                        <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#10b981; box-shadow:0 0 6px #10b981;"></span>
                        <a href="${data.public_url}" target="_blank" style="color:var(--primary); text-decoration:none; font-weight:700; font-size:11px;" title="Permanent Public Gateway">
                            ${data.public_url.replace('https://', '')}
                        </a>
                        <button onclick="copyPublicUrl('${data.public_url}')" title="Copy Public URL" style="background:none; border:none; color:var(--text-muted); cursor:pointer; padding:2px; display:inline-flex; align-items:center;">
                            <i data-lucide="copy" style="width:12px; height:12px;"></i>
                        </button>
                    </div>
                    <div style="font-size:10px; color:var(--text-muted);">Offline: <a href="${offlineUrl}" target="_blank" style="color:inherit; text-decoration:underline;">${offlineUrl}</a></div>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:2px; width:100%; text-align:center;">
                    <div style="display:flex; align-items:center; justify-content:center; gap:5px;">
                        <i data-lucide="shield-check" style="width:13px; height:13px; color:var(--success);"></i>
                        <a href="${offlineUrl}" target="_blank" style="color:var(--text-main); font-weight:700; font-size:11px; text-decoration:none;">
                            ${offlineUrl}
                        </a>
                        <button onclick="copyPublicUrl('${offlineUrl}')" title="Copy Offline Link" style="background:none; border:none; color:var(--text-muted); cursor:pointer; padding:2px; display:inline-flex; align-items:center;">
                            <i data-lucide="copy" style="width:12px; height:12px;"></i>
                        </button>
                    </div>
                    <div style="font-size:10px; color:var(--text-muted); cursor:pointer;" onclick="openOfflineQrModal()" title="Click to view QR Code">
                        Wi-Fi IP: http://${data.ip}:${data.port || 8550} 📱
                    </div>
                </div>
            `;
        }
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        document.getElementById('web-access-ip').textContent = `Web Access: Localhost`;
    }
}

// ==========================================
// THEMING SYSTEM
// ==========================================
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const themeIcon = document.getElementById('theme-icon');
    if (theme === 'dark') {
        themeIcon.setAttribute('data-lucide', 'sun');
    } else {
        themeIcon.setAttribute('data-lucide', 'moon');
    }
    lucide.createIcons();
}

// ==========================================
// SIDEBAR DRAWER TOGGLE
// ==========================================
function toggleSidebar(show) {
    const sidebar = document.getElementById('app-sidebar');
    if (show) {
        sidebar.classList.add('open');
    } else {
        sidebar.classList.remove('open');
    }
}

// ==========================================
// TOAST ALERTS HELPER
// ==========================================
function showAlert(message, isSuccess = true) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${isSuccess ? 'success' : 'danger'}`;
    
    const iconName = isSuccess ? 'check-circle' : 'alert-triangle';
    toast.innerHTML = `
        <i data-lucide="${iconName}"></i>
        <div class="toast-message">${message}</div>
    `;
    
    container.appendChild(toast);
    lucide.createIcons();
    
    // Auto-remove toast from DOM
    setTimeout(() => {
        toast.remove();
    }, 3500);
}

// ==========================================
// CONFIRMATION MODAL HELPER
// ==========================================
let confirmCallback = null;

function showConfirmDialog(title, text, onConfirm) {
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-text').textContent = text;
    document.getElementById('confirm-modal').classList.remove('hidden');
    confirmCallback = onConfirm;
}

function closeConfirmModal() {
    document.getElementById('confirm-modal').classList.add('hidden');
    confirmCallback = null;
}

// Hook confirm button click
document.getElementById('confirm-submit-btn').addEventListener('click', () => {
    if (confirmCallback) {
        confirmCallback();
    }
    closeConfirmModal();
});

// ==========================================
// FORM EDIT MODAL HELPER
// ==========================================
function showEditModal(title, formHTML) {
    document.getElementById('edit-modal-title').textContent = title;
    document.getElementById('edit-modal-body').innerHTML = formHTML;
    document.getElementById('edit-modal').classList.remove('hidden');
    lucide.createIcons();
}

function closeEditModal() {
    document.getElementById('edit-modal').classList.add('hidden');
    currentEditId = null;
}

// ==========================================
// ROUTER NAVIGATION
// ==========================================
function navigateTo(viewName, event) {
    if (event) {
        event.preventDefault();
    }
    activeView = viewName;
    
    // Reset edit state
    currentEditId = null;

    // Update active nav item styling
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('data-view') === viewName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Close sidebar on mobile
    toggleSidebar(false);

    // Update headers
    const viewTitles = {
        'dashboard': 'Dashboard Overview',
        'families': 'Families & Evacuees Directory',
        'rooms': 'Shelter Room Allocation',
        'inventory': 'Relief Goods Supplies',
        'distribution': 'Relief Goods Distribution Ledger',
        'users': 'System Operators Accounts'
    };
    document.getElementById('page-title').textContent = viewTitles[viewName] || 'Overview';

    // Render View Content
    renderView(viewName);
}

// Dispatch renderer
function renderView(viewName) {
    const contentArea = document.getElementById('view-content');
    contentArea.innerHTML = ''; // Clear previous contents

    switch (viewName) {
        case 'dashboard':
            renderDashboardView(contentArea);
            break;
        case 'families':
            renderFamiliesView(contentArea);
            break;
        case 'rooms':
            renderRoomsView(contentArea);
            break;
        case 'inventory':
            renderInventoryView(contentArea);
            break;
        case 'distribution':
            renderDistributionView(contentArea);
            break;
        case 'users':
            renderUsersView(contentArea);
            break;
        default:
            contentArea.innerHTML = `<p>View not found or Access Denied.</p>`;
    }
}

// ==========================================
// AUTHENTICATION HANDLERS
// ==========================================
function switchAuthTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.auth-form').forEach(f => f.classList.add('hidden'));
    
    if (tab === 'login') {
        document.getElementById('tab-login').classList.add('active');
        document.getElementById('login-form').classList.remove('hidden');
    } else {
        document.getElementById('tab-register').classList.add('active');
        document.getElementById('register-form').classList.remove('hidden');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await res.json();
        if (res.ok) {
            currentUser.userId = data.user_id;
            currentUser.username = data.username;
            currentUser.role = data.role;
            
            localStorage.setItem('user_id', data.user_id);
            localStorage.setItem('username', data.username);
            localStorage.setItem('role', data.role);
            
            showAlert(`Welcome back, ${data.username}!`);
            checkAuth();
        } else {
            showAlert(data.error || 'Invalid credentials.', false);
        }
    } catch (err) {
        showAlert('Connection error.', false);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    const role = document.getElementById('reg-role').value;

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, role })
        });
        
        const data = await res.json();
        if (res.ok) {
            showAlert('Account created successfully! Please sign in.');
            document.getElementById('reg-username').value = '';
            document.getElementById('reg-password').value = '';
            switchAuthTab('login');
        } else {
            showAlert(data.error || 'Username already exists.', false);
        }
    } catch (err) {
        showAlert('Registration failed.', false);
    }
}

function handleLogout() {
    currentUser = { userId: null, username: 'Guest', role: 'Staff' };
    localStorage.removeItem('user_id');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    checkAuth();
}

function triggerShutdown() {
    showConfirmDialog(
        "Shut Down Server",
        "Are you sure you want to shut down the application server? This will terminate the process and close the session.",
        async () => {
            document.body.innerHTML = `
                <div class="auth-wrapper" style="background: #0f172a; display: flex; align-items: center; justify-content: center;">
                    <div style="text-align: center; color: #ef4444;">
                        <i data-lucide="power" style="width: 80px; height: 80px; margin-bottom: 20px;"></i>
                        <h1 style="font-size: 32px; font-weight: 800; margin-bottom: 10px;">System Offline</h1>
                        <p style="color: #ffffff; font-size: 16px; margin-bottom: 5px;">The application server has been shut down successfully.</p>
                        <p style="color: #94a3b8; font-size: 14px;">All operations terminated. You can close this browser tab.</p>
                    </div>
                </div>
            `;
            lucide.createIcons();
            
            try {
                await fetch('/api/shutdown', { method: 'POST' });
            } catch (e) {
                // Server shuts down, so connection is expected to close
            }
        }
    );
}

// ==========================================
// DASHBOARD VIEW
// ==========================================
async function renderDashboardView(container) {
    container.innerHTML = `
        <!-- Quick Actions Bar -->
        <div class="quick-actions-bar">
            <div class="quick-actions-label">
                <i data-lucide="zap"></i> Quick Actions
            </div>
            <button class="btn btn-secondary btn-sm" onclick="navigateTo('families')">
                <i data-lucide="user-plus"></i> Register Family
            </button>
            <button class="btn btn-secondary btn-sm" onclick="navigateTo('rooms')">
                <i data-lucide="door-open"></i> Manage Rooms
            </button>
            <button class="btn btn-secondary btn-sm" onclick="navigateTo('inventory')">
                <i data-lucide="archive"></i> Restock Goods
            </button>
            <button class="btn btn-secondary btn-sm" onclick="navigateTo('distribution')">
                <i data-lucide="truck"></i> Issue Distribution
            </button>
        </div>

        <!-- Metrics Grid -->
        <div class="metrics-grid">
            <div class="metric-card indigo">
                <div class="metric-icon"><i data-lucide="home"></i></div>
                <div class="metric-info">
                    <span>Total Families</span>
                    <h3 id="stat-families">0</h3>
                    <div class="metric-trend">Registered Units</div>
                </div>
            </div>
            <div class="metric-card emerald">
                <div class="metric-icon"><i data-lucide="user-check"></i></div>
                <div class="metric-info">
                    <span>Total Evacuees</span>
                    <h3 id="stat-evacuees">0</h3>
                    <div class="metric-trend">Sheltered Individuals</div>
                </div>
            </div>
            <div class="metric-card amber">
                <div class="metric-icon"><i data-lucide="bed"></i></div>
                <div class="metric-info">
                    <span>Bed Occupancy</span>
                    <h3 id="stat-rooms">0 / 0</h3>
                    <div class="metric-trend">Occupied / Total Capacity</div>
                </div>
            </div>
            <div class="metric-card pink">
                <div class="metric-icon"><i data-lucide="package"></i></div>
                <div class="metric-info">
                    <span>Inventory Items</span>
                    <h3 id="stat-inventory">0</h3>
                    <div class="metric-trend">Active Supply Catalog</div>
                </div>
            </div>
        </div>

        <!-- Shelter Capacity Visual Meter Card -->
        <div class="capacity-card-widget">
            <div class="capacity-widget-header">
                <div class="capacity-title">
                    <i data-lucide="activity"></i> Shelter Facility Occupancy Meter
                </div>
                <span id="capacity-badge" class="badge badge-success">Normal Level</span>
            </div>
            <div class="capacity-large-meter">
                <div id="capacity-large-fill" class="capacity-large-fill" style="width: 0%; background: linear-gradient(90deg, var(--accent) 0%, var(--info) 100%);"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; color: var(--text-secondary);">
                <span id="capacity-details">0 of 0 spaces occupied</span>
                <span id="capacity-percent">0% Occupied</span>
            </div>
        </div>
        
        <!-- Recent Tables Panel -->
        <div class="dashboard-tables">
            <div class="panel-card">
                <div class="panel-header">
                    <span class="panel-title"><i data-lucide="clock"></i> Recent Check-ins</span>
                    <button class="btn-link" onclick="navigateTo('families')">View All <i data-lucide="chevron-right" style="width:14px; height:14px;"></i></button>
                </div>
                <div class="table-responsive">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Full Name</th>
                                <th>Age</th>
                                <th>Gender</th>
                                <th>Room Assignment</th>
                            </tr>
                        </thead>
                        <tbody id="recent-checkins-body">
                            <tr><td colspan="4" class="no-data-cell">Loading check-ins...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="panel-card">
                <div class="panel-header">
                    <span class="panel-title"><i data-lucide="truck"></i> Recent Distributions</span>
                    <button class="btn-link" onclick="navigateTo('distribution')">View All <i data-lucide="chevron-right" style="width:14px; height:14px;"></i></button>
                </div>
                <div class="table-responsive">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Family</th>
                                <th>Item Issued</th>
                                <th>Qty</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody id="recent-issues-body">
                            <tr><td colspan="4" class="no-data-cell">Loading distributions...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    lucide.createIcons();

    // Fetch dashboard data
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        
        document.getElementById('stat-families').textContent = data.total_families;
        document.getElementById('stat-evacuees').textContent = data.total_evacuees;
        document.getElementById('stat-rooms').textContent = `${data.total_occupied} / ${data.total_capacity}`;
        document.getElementById('stat-inventory').textContent = data.total_items;

        // Occupancy calculation
        const pct = data.total_capacity > 0 ? Math.min(100, Math.round((data.total_occupied / data.total_capacity) * 100)) : 0;
        const fillBar = document.getElementById('capacity-large-fill');
        const badge = document.getElementById('capacity-badge');
        const details = document.getElementById('capacity-details');
        const percentLabel = document.getElementById('capacity-percent');

        if (fillBar && badge && details && percentLabel) {
            fillBar.style.width = `${pct}%`;
            percentLabel.textContent = `${pct}% Occupied`;
            details.textContent = `${data.total_occupied} of ${data.total_capacity} shelter spaces allocated`;

            if (pct >= 90) {
                badge.className = 'badge badge-danger';
                badge.textContent = 'Critical Occupancy';
                fillBar.style.background = 'linear-gradient(90deg, var(--warning) 0%, var(--danger) 100%)';
            } else if (pct >= 75) {
                badge.className = 'badge badge-warning';
                badge.textContent = 'High Demand';
                fillBar.style.background = 'linear-gradient(90deg, var(--accent) 0%, var(--warning) 100%)';
            } else {
                badge.className = 'badge badge-success';
                badge.textContent = 'Normal Capacity';
                fillBar.style.background = 'linear-gradient(90deg, var(--accent) 0%, var(--info) 100%)';
            }
        }

        // Render recent check-ins
        const checkinsBody = document.getElementById('recent-checkins-body');
        checkinsBody.innerHTML = '';
        if (data.recent_evacuees.length > 0) {
            data.recent_evacuees.forEach(e => {
                const genderClass = e.gender === 'Male' ? 'badge-info' : e.gender === 'Female' ? 'badge-success' : 'badge-warning';
                checkinsBody.innerHTML += `
                    <tr>
                        <td><strong>${e.fullname}</strong></td>
                        <td>${e.age} yrs</td>
                        <td><span class="badge ${genderClass}">${e.gender}</span></td>
                        <td>${e.room_name ? `<span class="badge badge-info"><i data-lucide="door-open" style="width:12px; height:12px; margin-right:4px;"></i> ${e.room_name}</span>` : '<span class="badge badge-warning">Unassigned</span>'}</td>
                    </tr>
                `;
            });
            lucide.createIcons();
        } else {
            checkinsBody.innerHTML = `
                <tr>
                    <td colspan="4" class="no-data-cell">
                        <div class="empty-state-box">
                            <i data-lucide="users"></i>
                            <p>No recent check-ins recorded yet.</p>
                        </div>
                    </td>
                </tr>
            `;
            lucide.createIcons();
        }

        // Render recent issues
        const issuesBody = document.getElementById('recent-issues-body');
        issuesBody.innerHTML = '';
        if (data.recent_distributions.length > 0) {
            data.recent_distributions.forEach(d => {
                issuesBody.innerHTML += `
                    <tr>
                        <td><strong>${d.family_name}</strong></td>
                        <td>${d.item_name}</td>
                        <td><span class="badge badge-info">${d.quantity} ${d.unit}</span></td>
                        <td><span class="text-muted" style="font-size:12px;">${d.distribution_date}</span></td>
                    </tr>
                `;
            });
            lucide.createIcons();
        } else {
            issuesBody.innerHTML = `
                <tr>
                    <td colspan="4" class="no-data-cell">
                        <div class="empty-state-box">
                            <i data-lucide="box"></i>
                            <p>No distribution records found.</p>
                        </div>
                    </td>
                </tr>
            `;
            lucide.createIcons();
        }
        
    } catch (e) {
        showAlert('Error loading dashboard stats.', false);
    }
}

// ==========================================
// FAMILIES & EVACUEES VIEW
// ==========================================
let activeSubTab = 'families';

function renderFamiliesView(container) {
    container.innerHTML = `
        <div class="sub-tabs-container">
            <button class="btn-sub-tab ${activeSubTab === 'families' ? 'active' : ''}" onclick="toggleFamiliesSubTab('families')">
                <i data-lucide="home"></i> Family Directory
            </button>
            <button class="btn-sub-tab ${activeSubTab === 'evacuees' ? 'active' : ''}" onclick="toggleFamiliesSubTab('evacuees')">
                <i data-lucide="users"></i> Evacuee Registry
            </button>
        </div>
        <div id="sub-tab-content"></div>
    `;
    
    lucide.createIcons();
    renderFamiliesSubTab(activeSubTab);
}

function toggleFamiliesSubTab(tab) {
    activeSubTab = tab;
    document.querySelectorAll('.btn-sub-tab').forEach(b => {
        if (b.innerText.toLowerCase().includes(tab === 'families' ? 'family' : 'evacuee')) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });
    renderFamiliesSubTab(tab);
}

function renderFamiliesSubTab(tab) {
    const subTabContent = document.getElementById('sub-tab-content');
    subTabContent.innerHTML = '';

    if (tab === 'families') {
        subTabContent.innerHTML = `
            <div class="split-layout">
                <!-- Register Family Form -->
                <div class="sidebar-form-panel">
                    <div class="panel-card">
                        <h3 class="panel-title"><i data-lucide="home"></i> Register New Family</h3>
                        <hr style="border: 0; border-top: 1px solid var(--border-color);">
                        <form onsubmit="saveFamily(event)">
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label for="fam-name">Family Surname</label>
                                <input type="text" id="fam-name" placeholder="Surname" required>
                            </div>
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label for="fam-contact">Contact Number</label>
                                <input type="text" id="fam-contact" placeholder="e.g. +63 912 345 6789">
                            </div>
                            <div class="form-group" style="margin-bottom: 20px;">
                                <label for="fam-address">Home Address / Origin</label>
                                <textarea id="fam-address" placeholder="Address"></textarea>
                            </div>
                            <button type="submit" class="btn btn-primary btn-block">
                                <i data-lucide="plus-circle"></i> Save Family
                            </button>
                        </form>
                    </div>
                </div>
                
                <!-- Families List -->
                <div class="main-database-panel">
                    <div class="panel-card">
                        <div class="database-header">
                            <h3 class="panel-title">Families Database</h3>
                            <div class="search-field-container">
                                <i data-lucide="search"></i>
                                <input type="text" id="fam-search" placeholder="Search family..." oninput="loadFamilies(this.value)">
                            </div>
                        </div>
                        <hr style="border: 0; border-top: 1px solid var(--border-color);">
                        <div class="table-responsive">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Family Name</th>
                                        <th>Contact</th>
                                        <th>Address</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="families-table-body">
                                    <tr><td colspan="5" class="no-data-cell">Loading families...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
        loadFamilies();
    } else {
        subTabContent.innerHTML = `
            <div class="split-layout">
                <!-- Register Evacuee Form -->
                <div class="sidebar-form-panel">
                    <div class="panel-card">
                        <h3 class="panel-title"><i data-lucide="user-plus"></i> Register Evacuee</h3>
                        <hr style="border: 0; border-top: 1px solid var(--border-color);">
                        <form onsubmit="saveEvacuee(event)">
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label for="evac-name">Full Name</label>
                                <input type="text" id="evac-name" placeholder="Full name" required>
                            </div>
                            <div class="form-row" style="margin-bottom: 15px;">
                                <div class="form-group">
                                    <label for="evac-age">Age</label>
                                    <input type="number" id="evac-age" min="0" placeholder="Age" required>
                                </div>
                                <div class="form-group">
                                    <label for="evac-gender">Gender</label>
                                    <select id="evac-gender">
                                        <option value="Male">Male</option>
                                        <option value="Female">Female</option>
                                        <option value="Other">Other</option>
                                    </select>
                                </div>
                            </div>
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label for="evac-med">Medical Notes</label>
                                <input type="text" id="evac-med" placeholder="Medical conditions / none">
                            </div>
                            <div class="form-group" style="margin-bottom: 15px;">
                                <label for="evac-family">Family Association</label>
                                <select id="evac-family" required>
                                    <option value="" disabled selected>-- Select Family --</option>
                                </select>
                            </div>
                            <div class="form-group" style="margin-bottom: 20px;">
                                <label for="evac-room">Room Assignment</label>
                                <select id="evac-room">
                                    <option value="">-- No Room Assignment --</option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-primary btn-block">
                                <i data-lucide="plus-circle"></i> Save Evacuee
                            </button>
                        </form>
                    </div>
                </div>
                
                <!-- Evacuees List -->
                <div class="main-database-panel">
                    <div class="panel-card">
                        <div class="database-header">
                            <h3 class="panel-title">Evacuee Registry Database</h3>
                            <div class="search-field-container">
                                <i data-lucide="search"></i>
                                <input type="text" id="evac-search" placeholder="Search evacuee..." oninput="loadEvacuees(this.value)">
                            </div>
                        </div>
                        <hr style="border: 0; border-top: 1px solid var(--border-color);">
                        <div class="table-responsive">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>Full Name</th>
                                        <th>Age</th>
                                        <th>Gender</th>
                                        <th>Family</th>
                                        <th>Medical Note</th>
                                        <th>Room</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="evacuees-table-body">
                                    <tr><td colspan="7" class="no-data-cell">Loading evacuees...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
        loadEvacuees();
        populateEvacueeDropdowns();
    }
    lucide.createIcons();
}

async function loadFamilies(search = '') {
    try {
        const res = await fetch(`/api/families?search=${encodeURIComponent(search)}`);
        const families = await res.json();
        currentFamilies = families; // cache it
        
        const body = document.getElementById('families-table-body');
        body.innerHTML = '';
        
        if (families.length > 0) {
            families.forEach(f => {
                const famName = escapeHtml(f.family_name);
                const contact = escapeHtml(f.contact_number) || 'N/A';
                const addr = escapeHtml(f.address) || 'N/A';
                body.innerHTML += `
                    <tr>
                        <td><span class="text-muted">#${f.family_id}</span></td>
                        <td><strong>${famName}</strong></td>
                        <td>${contact}</td>
                        <td>${addr}</td>
                        <td>
                            <div style="display: flex; gap: 5px;">
                                <button class="btn-icon-only" onclick="openEditFamilyModal(${f.family_id})" title="Edit">
                                    <i data-lucide="edit-3" style="width: 16px; height: 16px; color: var(--text-secondary);"></i>
                                </button>
                                <button class="btn-icon-only text-danger" onclick="deleteFamily(${f.family_id})" title="Delete">
                                    <i data-lucide="trash-2" style="width: 16px; height: 16px; color: var(--danger);"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            lucide.createIcons();
        } else {
            body.innerHTML = `<tr><td colspan="5" class="no-data-cell">No families registered.</td></tr>`;
        }
    } catch (e) {
        showAlert('Failed to load families.', false);
    }
}

async function saveFamily(e) {
    e.preventDefault();
    const family_name = document.getElementById('fam-name').value.trim();
    const contact_number = document.getElementById('fam-contact').value.trim();
    const address = document.getElementById('fam-address').value.trim();

    if (!family_name) {
        showAlert('Family Name is required.', false);
        return;
    }

    try {
        const res = await fetch('/api/families', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ family_name, contact_number, address })
        });
        
        if (res.ok) {
            showAlert('Family registered successfully!');
            document.getElementById('fam-name').value = '';
            document.getElementById('fam-contact').value = '';
            document.getElementById('fam-address').value = '';
            loadFamilies();
        } else {
            const data = await res.json();
            showAlert(data.error || 'Failed to save family.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

function openEditFamilyModal(id) {
    const f = currentFamilies.find(item => item.family_id === id);
    if (!f) return;
    currentEditId = id;
    const name = escapeHtml(f.family_name);
    const contact = escapeHtml(f.contact_number || '');
    const address = escapeHtml(f.address || '');
    const formHTML = `
        <form onsubmit="updateFamily(event)" class="auth-form">
            <div class="form-group">
                <label for="edit-fam-name">Family Name</label>
                <input type="text" id="edit-fam-name" value="${name}" required>
            </div>
            <div class="form-group">
                <label for="edit-fam-contact">Contact Number</label>
                <input type="text" id="edit-fam-contact" value="${contact}">
            </div>
            <div class="form-group">
                <label for="edit-fam-address">Address</label>
                <textarea id="edit-fam-address">${address}</textarea>
            </div>
            <div class="modal-actions" style="margin-top: 15px;">
                <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Changes</button>
            </div>
        </form>
    `;
    showEditModal("Edit Family Details", formHTML);
}

async function updateFamily(e) {
    e.preventDefault();
    const family_name = document.getElementById('edit-fam-name').value.trim();
    const contact_number = document.getElementById('edit-fam-contact').value.trim();
    const address = document.getElementById('edit-fam-address').value.trim();

    try {
        const res = await fetch(`/api/families/${currentEditId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ family_name, contact_number, address })
        });
        
        if (res.ok) {
            showAlert('Family details updated!');
            closeEditModal();
            loadFamilies();
        } else {
            const data = await res.json();
            showAlert(data.error || 'Failed to update family.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

function deleteFamily(id) {
    showConfirmDialog(
        "Delete Family Record",
        "Are you sure? This will delete the family and all associated evacuees, room assignments, and distributions.",
        async () => {
            try {
                const res = await fetch(`/api/families/${id}`, { method: 'DELETE' });
                if (res.ok) {
                    showAlert('Family and associated evacuees removed successfully.');
                    loadFamilies();
                } else {
                    showAlert('Failed to delete family record.', false);
                }
            } catch (e) {
                showAlert('Server connection error.', false);
            }
        }
    );
}

async function loadEvacuees(search = '') {
    try {
        const res = await fetch(`/api/evacuees?search=${encodeURIComponent(search)}`);
        const evacuees = await res.json();
        currentEvacuees = evacuees; // cache it
        
        const body = document.getElementById('evacuees-table-body');
        body.innerHTML = '';
        
        if (evacuees.length > 0) {
            evacuees.forEach(e => {
                const fullname = escapeHtml(e.fullname);
                const famName = escapeHtml(e.family_name);
                const genderClass = e.gender === 'Male' ? 'badge-info' : e.gender === 'Female' ? 'badge-success' : 'badge-warning';
                
                const medVisible = e.medical_condition && e.medical_condition.toLowerCase() !== 'none' && e.medical_condition.trim() !== '';
                const medCell = medVisible 
                    ? `<span class="badge badge-danger">${escapeHtml(e.medical_condition)}</span>` 
                    : `<span class="text-muted">None</span>`;
                    
                const roomCell = e.room_name 
                    ? `<span class="badge badge-info">${escapeHtml(e.room_name)}</span>` 
                    : `<span class="badge badge-warning">Unassigned</span>`;
                
                body.innerHTML += `
                    <tr>
                        <td><strong>${fullname}</strong></td>
                        <td>${e.age !== null && e.age !== undefined ? e.age : 'N/A'}</td>
                        <td><span class="badge ${genderClass}">${e.gender}</span></td>
                        <td>${famName}</td>
                        <td>${medCell}</td>
                        <td>${roomCell}</td>
                        <td>
                            <div style="display: flex; gap: 5px;">
                                <button class="btn-icon-only" onclick="openEditEvacueeModal(${e.evacuee_id})" title="Edit">
                                    <i data-lucide="edit-3" style="width: 16px; height: 16px; color: var(--text-secondary);"></i>
                                </button>
                                <button class="btn-icon-only text-danger" onclick="deleteEvacuee(${e.evacuee_id})" title="Delete">
                                    <i data-lucide="trash-2" style="width: 16px; height: 16px; color: var(--danger);"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            lucide.createIcons();
        } else {
            body.innerHTML = `<tr><td colspan="7" class="no-data-cell">No evacuees registered.</td></tr>`;
        }
    } catch (e) {
        showAlert('Failed to load evacuees.', false);
    }
}

async function populateEvacueeDropdowns() {
    try {
        const famRes = await fetch('/api/families');
        const families = await famRes.json();
        
        const roomRes = await fetch('/api/rooms');
        const rooms = await roomRes.json();
        currentRooms = rooms; // cache it

        const famSel = document.getElementById('evac-family');
        famSel.innerHTML = '<option value="" disabled selected>-- Select Family --</option>';
        families.forEach(f => {
            famSel.innerHTML += `<option value="${f.family_id}">${escapeHtml(f.family_name)} (#${f.family_id})</option>`;
        });

        const roomSel = document.getElementById('evac-room');
        roomSel.innerHTML = '<option value="">-- No Room Assignment --</option>';
        rooms.forEach(r => {
            const isFull = r.occupied >= r.capacity;
            const disabledAttr = isFull ? 'disabled' : '';
            roomSel.innerHTML += `<option value="${r.room_id}" ${disabledAttr}>${escapeHtml(r.room_name)} (${r.occupied}/${r.capacity}${isFull ? ' - FULL' : ''})</option>`;
        });
    } catch (e) {
        showAlert('Error populating form dropdowns.', false);
    }
}

async function saveEvacuee(e) {
    e.preventDefault();
    const fullname = document.getElementById('evac-name').value.trim();
    const ageVal = document.getElementById('evac-age').value;
    const age = ageVal !== '' ? parseInt(ageVal) : null;
    const gender = document.getElementById('evac-gender').value;
    const medical_condition = document.getElementById('evac-med').value.trim();
    const family_id = parseInt(document.getElementById('evac-family').value);
    const room_id_val = document.getElementById('evac-room').value;
    const room_id = room_id_val ? parseInt(room_id_val) : null;

    if (!fullname || !family_id) {
        showAlert('Full Name and Family Association are required.', false);
        return;
    }

    try {
        const res = await fetch('/api/evacuees', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fullname, age, gender, medical_condition, family_id, room_id })
        });
        
        const data = await res.json();
        if (res.ok) {
            showAlert('Evacuee registered successfully!');
            document.getElementById('evac-name').value = '';
            document.getElementById('evac-age').value = '';
            document.getElementById('evac-med').value = '';
            document.getElementById('evac-family').value = '';
            document.getElementById('evac-room').value = '';
            loadEvacuees();
            populateEvacueeDropdowns();
        } else {
            showAlert(data.error || 'Failed to save evacuee.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

async function openEditEvacueeModal(id) {
    const eObj = currentEvacuees.find(item => item.evacuee_id === id);
    if (!eObj) return;
    currentEditId = id;
    
    const fullname = escapeHtml(eObj.fullname);
    const age = eObj.age !== null && eObj.age !== undefined ? eObj.age : '';
    const gender = eObj.gender || 'Other';
    const med = escapeHtml(eObj.medical_condition || '');
    const family_id = eObj.family_id;
    const current_room_id = eObj.room_id;
    
    try {
        const famRes = await fetch('/api/families');
        const families = await famRes.json();
        
        const roomRes = await fetch('/api/rooms');
        const rooms = await roomRes.json();

        let famOptionsHTML = '';
        families.forEach(f => {
            const selected = f.family_id === family_id ? 'selected' : '';
            famOptionsHTML += `<option value="${f.family_id}" ${selected}>${escapeHtml(f.family_name)} (#${f.family_id})</option>`;
        });

        let roomOptionsHTML = '<option value="">-- No Room Assignment --</option>';
        rooms.forEach(r => {
            const isCurrent = r.room_id === current_room_id;
            const isFull = (r.occupied >= r.capacity) && !isCurrent;
            const selected = isCurrent ? 'selected' : '';
            const disabledAttr = isFull ? 'disabled' : '';
            roomOptionsHTML += `<option value="${r.room_id}" ${selected} ${disabledAttr}>${escapeHtml(r.room_name)} (${r.occupied}/${r.capacity}${isFull ? ' - FULL' : ''})</option>`;
        });

        const formHTML = `
            <form onsubmit="updateEvacuee(event)" class="auth-form">
                <div class="form-group">
                    <label for="edit-evac-name">Full Name</label>
                    <input type="text" id="edit-evac-name" value="${fullname}" required>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="edit-evac-age">Age</label>
                        <input type="number" id="edit-evac-age" min="0" value="${age}">
                    </div>
                    <div class="form-group">
                        <label for="edit-evac-gender">Gender</label>
                        <select id="edit-evac-gender">
                            <option value="Male" ${gender === 'Male' ? 'selected' : ''}>Male</option>
                            <option value="Female" ${gender === 'Female' ? 'selected' : ''}>Female</option>
                            <option value="Other" ${gender === 'Other' ? 'selected' : ''}>Other</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label for="edit-evac-med">Medical Notes</label>
                    <input type="text" id="edit-evac-med" value="${med}">
                </div>
                <div class="form-group">
                    <label for="edit-evac-family">Family Association</label>
                    <select id="edit-evac-family" required>
                        ${famOptionsHTML}
                    </select>
                </div>
                <div class="form-group">
                    <label for="edit-evac-room">Room Assignment</label>
                    <select id="edit-evac-room">
                        ${roomOptionsHTML}
                    </select>
                </div>
                <div class="modal-actions" style="margin-top: 15px;">
                    <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                </div>
            </form>
        `;
        
        showEditModal("Edit Evacuee Details", formHTML);
    } catch (e) {
        showAlert('Failed to open edit modal.', false);
    }
}

async function updateEvacuee(e) {
    e.preventDefault();
    const fullname = document.getElementById('edit-evac-name').value.trim();
    const age = parseInt(document.getElementById('edit-evac-age').value);
    const gender = document.getElementById('edit-evac-gender').value;
    const medical_condition = document.getElementById('edit-evac-med').value.trim();
    const family_id = parseInt(document.getElementById('edit-evac-family').value);
    const room_id_val = document.getElementById('edit-evac-room').value;
    const room_id = room_id_val ? parseInt(room_id_val) : null;

    try {
        const res = await fetch(`/api/evacuees/${currentEditId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fullname, age, gender, medical_condition, family_id, room_id })
        });
        
        const data = await res.json();
        if (res.ok) {
            showAlert('Evacuee details modified successfully!');
            closeEditModal();
            loadEvacuees();
        } else {
            showAlert(data.error || 'Failed to update evacuee.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

function deleteEvacuee(id) {
    showConfirmDialog(
        "Deregister Evacuee",
        "Are you sure you want to remove this evacuee and free up their room assignment?",
        async () => {
            try {
                const res = await fetch(`/api/evacuees/${id}`, { method: 'DELETE' });
                if (res.ok) {
                    showAlert('Evacuee deregistered successfully.');
                    loadEvacuees();
                } else {
                    showAlert('Failed to delete evacuee record.', false);
                }
            } catch (e) {
                showAlert('Server connection error.', false);
            }
        }
    );
}

// ==========================================
// ROOMS MANAGEMENT VIEW
// ==========================================
function renderRoomsView(container) {
    container.innerHTML = `
        <div class="split-layout">
            <!-- Add Room Form -->
            <div class="sidebar-form-panel">
                <div class="panel-card">
                    <h3 class="panel-title"><i data-lucide="door-open"></i> Add New Room</h3>
                    <hr style="border: 0; border-top: 1px solid var(--border-color);">
                    <form onsubmit="saveRoom(event)">
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label for="room-name">Room Name / Designation</label>
                            <input type="text" id="room-name" placeholder="e.g. Gym East Wing" required>
                        </div>
                        <div class="form-group" style="margin-bottom: 20px;">
                            <label for="room-capacity">Total Capacity (People)</label>
                            <input type="number" id="room-capacity" min="1" placeholder="e.g. 50" required>
                        </div>
                        <button type="submit" class="btn btn-primary btn-block">
                            <i data-lucide="plus-circle"></i> Save Room
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Rooms List -->
            <div class="main-database-panel">
                <div class="panel-card">
                    <div class="database-header">
                        <h3 class="panel-title">Rooms Database</h3>
                        <div class="search-field-container">
                            <i data-lucide="search"></i>
                            <input type="text" id="room-search" placeholder="Search room..." oninput="loadRooms(this.value)">
                        </div>
                    </div>
                    <hr style="border: 0; border-top: 1px solid var(--border-color);">
                    <div class="table-responsive">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Room Name</th>
                                    <th>Occupancy Level</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="rooms-table-body">
                                <tr><td colspan="5" class="no-data-cell">Loading rooms...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;
    lucide.createIcons();
    loadRooms();
}

async function loadRooms(search = '') {
    try {
        const res = await fetch(`/api/rooms?search=${encodeURIComponent(search)}`);
        const rooms = await res.json();
        currentRooms = rooms; // cache it
        
        const body = document.getElementById('rooms-table-body');
        body.innerHTML = '';
        
        if (rooms.length > 0) {
            rooms.forEach(r => {
                const roomName = escapeHtml(r.room_name);
                const rate = r.capacity > 0 ? Math.round((r.occupied / r.capacity) * 100) : 0;
                
                // Color configuration
                let barColorClass = 'bg-success';
                let statusText = 'Available';
                let statusClass = 'badge-success';
                
                if (rate >= 100) {
                    barColorClass = 'bg-danger';
                    statusText = 'Full';
                    statusClass = 'badge-danger';
                } else if (rate >= 80) {
                    barColorClass = 'bg-warning';
                    statusText = 'Near Limit';
                    statusClass = 'badge-warning';
                }
                
                body.innerHTML += `
                    <tr>
                        <td><span class="text-muted">#${r.room_id}</span></td>
                        <td><strong>${roomName}</strong></td>
                        <td>
                            <div class="occupancy-cell">
                                <div class="occupancy-info">
                                    <strong>${r.occupied} / ${r.capacity} individuals</strong>
                                    <span>${rate}%</span>
                                </div>
                                <div class="progress-bar-container">
                                    <div class="progress-bar ${barColorClass}" style="width: ${Math.min(100, rate)}%; background-color: ${rate >= 100 ? 'var(--danger)' : rate >= 80 ? 'var(--warning)' : 'var(--success)'}"></div>
                                </div>
                            </div>
                        </td>
                        <td><span class="badge ${statusClass}">${statusText}</span></td>
                        <td>
                            <div style="display: flex; gap: 5px;">
                                <button class="btn-icon-only" onclick="openEditRoomModal(${r.room_id})" title="Edit">
                                    <i data-lucide="edit-3" style="width: 16px; height: 16px; color: var(--text-secondary);"></i>
                                </button>
                                <button class="btn-icon-only text-danger" onclick="deleteRoom(${r.room_id})" title="Delete">
                                    <i data-lucide="trash-2" style="width: 16px; height: 16px; color: var(--danger);"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            lucide.createIcons();
        } else {
            body.innerHTML = `<tr><td colspan="5" class="no-data-cell">No rooms configured yet.</td></tr>`;
        }
    } catch (e) {
        showAlert('Failed to load rooms.', false);
    }
}

async function saveRoom(e) {
    e.preventDefault();
    const room_name = document.getElementById('room-name').value.trim();
    const capacity = parseInt(document.getElementById('room-capacity').value);

    if (!room_name || isNaN(capacity) || capacity <= 0) {
        showAlert('Valid name and positive capacity are required.', false);
        return;
    }

    try {
        const res = await fetch('/api/rooms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_name, capacity })
        });
        
        if (res.ok) {
            showAlert('Evacuation room added successfully!');
            document.getElementById('room-name').value = '';
            document.getElementById('room-capacity').value = '';
            loadRooms();
        } else {
            const data = await res.json();
            showAlert(data.error || 'Failed to save room.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

function openEditRoomModal(id) {
    const r = currentRooms.find(item => item.room_id === id);
    if (!r) return;
    currentEditId = id;
    const name = escapeHtml(r.room_name);
    const capacity = r.capacity;
    const formHTML = `
        <form onsubmit="updateRoom(event)" class="auth-form">
            <div class="form-group">
                <label for="edit-room-name">Room Name</label>
                <input type="text" id="edit-room-name" value="${name}" required>
            </div>
            <div class="form-group">
                <label for="edit-room-capacity">Room Capacity</label>
                <input type="number" id="edit-room-capacity" min="1" value="${capacity}" required>
            </div>
            <div class="modal-actions" style="margin-top: 15px;">
                <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Changes</button>
            </div>
        </form>
    `;
    showEditModal("Edit Room Details", formHTML);
}

async function updateRoom(e) {
    e.preventDefault();
    const room_name = document.getElementById('edit-room-name').value.trim();
    const capacity = parseInt(document.getElementById('edit-room-capacity').value);

    if (!room_name || isNaN(capacity) || capacity <= 0) {
        showAlert('Valid room name and capacity are required.', false);
        return;
    }

    try {
        const res = await fetch(`/api/rooms/${currentEditId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_name, capacity })
        });
        
        if (res.ok) {
            showAlert('Room details modified successfully.');
            closeEditModal();
            loadRooms();
        } else {
            const data = await res.json();
            showAlert(data.error || 'Failed to update room.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

function deleteRoom(id) {
    showConfirmDialog(
        "Remove Evacuation Room",
        "Are you sure? This will delete the room and mark all assigned evacuees as 'Unassigned'.",
        async () => {
            try {
                const res = await fetch(`/api/rooms/${id}`, { method: 'DELETE' });
                if (res.ok) {
                    showAlert("Room removed. Registered evacuees in that room are now unassigned.");
                    loadRooms();
                } else {
                    showAlert('Failed to delete room.', false);
                }
            } catch (e) {
                showAlert('Server connection error.', false);
            }
        }
    );
}

// ==========================================
// INVENTORY SUPPLIES VIEW
// ==========================================
function renderInventoryView(container) {
    container.innerHTML = `
        <div class="split-layout">
            <!-- Add Item Form -->
            <div class="sidebar-form-panel">
                <div class="panel-card">
                    <h3 class="panel-title"><i data-lucide="archive"></i> Add New Item</h3>
                    <hr style="border: 0; border-top: 1px solid var(--border-color);">
                    <form onsubmit="saveInventory(event)">
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label for="inv-name">Item Name</label>
                            <input type="text" id="inv-name" placeholder="e.g. Hygiene Kit" required>
                        </div>
                        <div class="form-row" style="margin-bottom: 20px;">
                            <div class="form-group">
                                <label for="inv-qty">Quantity</label>
                                <input type="number" id="inv-qty" min="0" placeholder="e.g. 100" required>
                            </div>
                            <div class="form-group">
                                <label for="inv-unit">Unit Measure</label>
                                <input type="text" id="inv-unit" placeholder="e.g. pcs" required>
                            </div>
                        </div>
                        <button type="submit" class="btn btn-primary btn-block">
                            <i data-lucide="plus-circle"></i> Save Item
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Inventory List -->
            <div class="main-database-panel">
                <div class="panel-card">
                    <div class="database-header">
                        <h3 class="panel-title">Current Supplies List</h3>
                        <div class="search-field-container">
                            <i data-lucide="search"></i>
                            <input type="text" id="inv-search" placeholder="Search items..." oninput="loadInventory(this.value)">
                        </div>
                    </div>
                    <hr style="border: 0; border-top: 1px solid var(--border-color);">
                    <div class="table-responsive">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Item Name</th>
                                    <th>Available Stock</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="inventory-table-body">
                                <tr><td colspan="5" class="no-data-cell">Loading items...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;
    lucide.createIcons();
    loadInventory();
}

async function loadInventory(search = '') {
    try {
        const res = await fetch(`/api/inventory?search=${encodeURIComponent(search)}`);
        const items = await res.json();
        currentInventory = items; // cache it
        
        const body = document.getElementById('inventory-table-body');
        body.innerHTML = '';
        
        if (items.length > 0) {
            items.forEach(item => {
                const itemName = escapeHtml(item.item_name);
                const unit = escapeHtml(item.unit);
                const statusText = item.quantity === 0 ? 'Out of Stock' : item.quantity <= 15 ? 'Low Stock' : 'Good Stock';
                const statusClass = item.quantity === 0 ? 'badge-danger' : item.quantity <= 15 ? 'badge-warning' : 'badge-success';
                
                body.innerHTML += `
                    <tr>
                        <td><span class="text-muted">#${item.item_id}</span></td>
                        <td><strong>${itemName}</strong></td>
                        <td><span class="badge badge-info">${item.quantity} ${unit}</span></td>
                        <td><span class="badge ${statusClass}">${statusText}</span></td>
                        <td>
                            <div style="display: flex; gap: 5px;">
                                <button class="btn-icon-only" onclick="openEditInventoryModal(${item.item_id})" title="Restock / Edit">
                                    <i data-lucide="archive-restore" style="width: 16px; height: 16px; color: var(--text-secondary);"></i>
                                </button>
                                <button class="btn-icon-only text-danger" onclick="deleteInventory(${item.item_id})" title="Delete">
                                    <i data-lucide="trash-2" style="width: 16px; height: 16px; color: var(--danger);"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            lucide.createIcons();
        } else {
            body.innerHTML = `<tr><td colspan="5" class="no-data-cell">No items in inventory.</td></tr>`;
        }
    } catch (e) {
        showAlert('Failed to load inventory supplies.', false);
    }
}

async function saveInventory(e) {
    e.preventDefault();
    const item_name = document.getElementById('inv-name').value.trim();
    const quantity = parseInt(document.getElementById('inv-qty').value);
    const unit = document.getElementById('inv-unit').value.trim();

    if (!item_name || isNaN(quantity) || quantity < 0 || !unit) {
        showAlert('All fields with valid values are required.', false);
        return;
    }

    try {
        const res = await fetch('/api/inventory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_name, quantity, unit })
        });
        
        if (res.ok) {
            showAlert('Inventory item listed successfully!');
            document.getElementById('inv-name').value = '';
            document.getElementById('inv-qty').value = '';
            document.getElementById('inv-unit').value = '';
            loadInventory();
        } else {
            const data = await res.json();
            showAlert(data.error || 'Failed to save inventory item.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

function openEditInventoryModal(id) {
    const item = currentInventory.find(x => x.item_id === id);
    if (!item) return;
    currentEditId = id;
    const name = escapeHtml(item.item_name);
    const quantity = item.quantity;
    const unit = escapeHtml(item.unit);
    const formHTML = `
        <form onsubmit="updateInventory(event)" class="auth-form">
            <div class="form-group">
                <label for="edit-inv-name">Item Name</label>
                <input type="text" id="edit-inv-name" value="${name}" required>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="edit-inv-qty">Quantity</label>
                    <input type="number" id="edit-inv-qty" min="0" value="${quantity}" required>
                </div>
                <div class="form-group">
                    <label for="edit-inv-unit">Unit Measure</label>
                    <input type="text" id="edit-inv-unit" value="${unit}" required>
                </div>
            </div>
            <div class="modal-actions" style="margin-top: 15px;">
                <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Stock</button>
            </div>
        </form>
    `;
    showEditModal("Restock & Edit Item", formHTML);
}

async function updateInventory(e) {
    e.preventDefault();
    const item_name = document.getElementById('edit-inv-name').value.trim();
    const quantity = parseInt(document.getElementById('edit-inv-qty').value);
    const unit = document.getElementById('edit-inv-unit').value.trim();

    try {
        const res = await fetch(`/api/inventory/${currentEditId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_name, quantity, unit })
        });
        
        if (res.ok) {
            showAlert('Inventory stock levels updated.');
            closeEditModal();
            loadInventory();
        } else {
            const data = await res.json();
            showAlert(data.error || 'Failed to update stock.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

function deleteInventory(id) {
    showConfirmDialog(
        "Delete Inventory Item",
        "Are you sure? Deleting this item will also delete all historical distributions recorded for it.",
        async () => {
            try {
                const res = await fetch(`/api/inventory/${id}`, { method: 'DELETE' });
                if (res.ok) {
                    showAlert('Inventory item and past distributions deleted successfully.');
                    loadInventory();
                } else {
                    showAlert('Failed to delete item.', false);
                }
            } catch (e) {
                showAlert('Server connection error.', false);
            }
        }
    );
}

// ==========================================
// DISTRIBUTIONS VIEW
// ==========================================
function renderDistributionView(container) {
    container.innerHTML = `
        <div class="split-layout">
            <!-- Distribute Form -->
            <div class="sidebar-form-panel">
                <div class="panel-card">
                    <h3 class="panel-title"><i data-lucide="truck"></i> Distribute Supplies</h3>
                    <hr style="border: 0; border-top: 1px solid var(--border-color);">
                    <form onsubmit="saveDistribution(event)">
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label for="dist-family">Select Recipient Family</label>
                            <select id="dist-family" required>
                                <option value="" disabled selected>-- Select Recipient --</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin-bottom: 5px;">
                            <label for="dist-item">Select Item to Distribute</label>
                            <select id="dist-item" required onchange="handleDistributionItemChange(this.value)">
                                <option value="" disabled selected>-- Select Item --</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <div class="web-access-ip" id="dist-max-stock" style="text-align: left; font-weight: bold; margin-bottom: 5px; color: var(--accent);"></div>
                            <label for="dist-qty">Quantity to Issue</label>
                            <input type="number" id="dist-qty" min="1" placeholder="e.g. 5" required>
                        </div>
                        <div class="form-group" style="margin-bottom: 20px;">
                            <label for="dist-date">Distribution Date</label>
                            <input type="date" id="dist-date" required>
                        </div>
                        <button type="submit" class="btn btn-primary btn-block">
                            <i data-lucide="truck"></i> Process Distribution
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Distribution Log -->
            <div class="main-database-panel">
                <div class="panel-card">
                    <div class="database-header">
                        <h3 class="panel-title">Distribution Ledger Log</h3>
                        <div class="search-field-container">
                            <i data-lucide="search"></i>
                            <input type="text" id="dist-search" placeholder="Search logs..." oninput="loadDistributions(this.value)">
                        </div>
                    </div>
                    <hr style="border: 0; border-top: 1px solid var(--border-color);">
                    <div class="table-responsive">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Ref ID</th>
                                    <th>Family Recipient</th>
                                    <th>Item Issued</th>
                                    <th>Quantity Issued</th>
                                    <th>Date Processed</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody id="distributions-table-body">
                                <tr><td colspan="6" class="no-data-cell">Loading ledger...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Set default date
    document.getElementById('dist-date').value = new Date().toISOString().substring(0, 10);
    
    lucide.createIcons();
    loadDistributions();
    populateDistributionDropdowns();
}

async function loadDistributions(search = '') {
    try {
        const res = await fetch(`/api/distributions?search=${encodeURIComponent(search)}`);
        const dists = await res.json();
        
        const body = document.getElementById('distributions-table-body');
        body.innerHTML = '';
        
        if (dists.length > 0) {
            dists.forEach(d => {
                body.innerHTML += `
                    <tr>
                        <td><span class="text-muted">#${d.distribution_id}</span></td>
                        <td><strong>${d.family_name}</strong></td>
                        <td>${d.item_name}</td>
                        <td><span class="badge badge-info">${d.quantity} ${d.unit}</span></td>
                        <td><strong>${d.distribution_date}</strong></td>
                        <td>
                            <button class="btn btn-danger" style="padding: 6px 12px; font-size: 12px; border-radius: 6px;" onclick="revertDistribution(${d.distribution_id})">
                                <i data-lucide="undo" style="width: 14px; height: 14px;"></i> Revert
                            </button>
                        </td>
                    </tr>
                `;
            });
            lucide.createIcons();
        } else {
            body.innerHTML = `<tr><td colspan="6" class="no-data-cell">No distributions recorded yet.</td></tr>`;
        }
    } catch (e) {
        showAlert('Failed to load distribution ledger.', false);
    }
}

async function populateDistributionDropdowns() {
    try {
        const famRes = await fetch('/api/families');
        const families = await famRes.json();
        
        const invRes = await fetch('/api/inventory');
        const inventory = await invRes.json();
        currentInventory = inventory; // cache it

        const famSel = document.getElementById('dist-family');
        famSel.innerHTML = '<option value="" disabled selected>-- Select Recipient --</option>';
        families.forEach(f => {
            famSel.innerHTML += `<option value="${f.family_id}">${f.family_name} (#${f.family_id})</option>`;
        });

        const invSel = document.getElementById('dist-item');
        invSel.innerHTML = '<option value="" disabled selected>-- Select Item --</option>';
        inventory.forEach(item => {
            const isEmpty = item.quantity <= 0;
            const disabledAttr = isEmpty ? 'disabled' : '';
            invSel.innerHTML += `<option value="${item.item_id}" ${disabledAttr}>${item.item_name} (Available: ${item.quantity} ${item.unit}${isEmpty ? ' - OUT OF STOCK' : ''})</option>`;
        });
    } catch (e) {
        showAlert('Error loading distribution forms.', false);
    }
}

function handleDistributionItemChange(itemId) {
    const selectedItem = currentInventory.find(i => i.item_id === parseInt(itemId));
    const maxStockLabel = document.getElementById('dist-max-stock');
    const qtyInput = document.getElementById('dist-qty');
    
    if (selectedItem) {
        maxStockLabel.textContent = `Max available: ${selectedItem.quantity} ${selectedItem.unit}`;
        qtyInput.max = selectedItem.quantity;
    } else {
        maxStockLabel.textContent = '';
        qtyInput.removeAttribute('max');
    }
}

async function saveDistribution(e) {
    e.preventDefault();
    const family_id = parseInt(document.getElementById('dist-family').value);
    const item_id = parseInt(document.getElementById('dist-item').value);
    const quantity = parseInt(document.getElementById('dist-qty').value);
    const distribution_date = document.getElementById('dist-date').value;

    const selectedItem = currentInventory.find(i => i.item_id === item_id);
    if (selectedItem && quantity > selectedItem.quantity) {
        showAlert('Insufficient stock to issue requested quantity!', false);
        return;
    }

    try {
        const res = await fetch('/api/distributions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ family_id, item_id, quantity, distribution_date })
        });
        
        if (res.ok) {
            showAlert('Supplies issued and inventory updated successfully!');
            renderDistributionView(document.getElementById('view-content'));
        } else {
            showAlert('Failed to process distribution.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

function revertDistribution(id) {
    showConfirmDialog(
        "Revert Supplies Distribution",
        "Reverting this distribution will return the issued quantities back into active inventory. Proceed?",
        async () => {
            try {
                const res = await fetch(`/api/distributions/revert/${id}`, { method: 'POST' });
                if (res.ok) {
                    showAlert('Distribution reverted successfully. Stock returned to inventory.');
                    renderDistributionView(document.getElementById('view-content'));
                } else {
                    showAlert('Failed to revert distribution.', false);
                }
            } catch (e) {
                showAlert('Server connection error.', false);
            }
        }
    );
}

// ==========================================
// SYSTEM OPERATORS VIEW (ADMIN ONLY)
// ==========================================
function renderUsersView(container) {
    if (currentUser.role !== 'Admin') {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--danger);">
                <i data-lucide="shield-alert" style="width: 64px; height: 64px; margin-bottom: 15px;"></i>
                <h2>Access Denied</h2>
                <p>Only Administrators are permitted to access this area.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    container.innerHTML = `
        <div class="split-layout">
            <!-- Create Operator Account Form -->
            <div class="sidebar-form-panel">
                <div class="panel-card">
                    <h3 class="panel-title"><i data-lucide="user-plus"></i> Create Operator Account</h3>
                    <hr style="border: 0; border-top: 1px solid var(--border-color);">
                    <form onsubmit="saveOperator(event)">
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label for="op-username">Username</label>
                            <input type="text" id="op-username" placeholder="Username" required>
                        </div>
                        <div class="form-group" style="margin-bottom: 15px;">
                            <label for="op-password">Password</label>
                            <input type="password" id="op-password" placeholder="Password" required>
                        </div>
                        <div class="form-group" style="margin-bottom: 20px;">
                            <label for="op-role">System Role Access</label>
                            <select id="op-role" required>
                                <option value="Staff">Staff (Standard Operations)</option>
                                <option value="Admin">Admin (Full Control)</option>
                            </select>
                        </div>
                        <button type="submit" class="btn btn-primary btn-block">
                            <i data-lucide="user-check"></i> Create Account
                        </button>
                    </form>
                </div>
            </div>
            
            <!-- Users List -->
            <div class="main-database-panel">
                <div class="panel-card">
                    <div class="database-header">
                        <h3 class="panel-title">System Operators</h3>
                        <div class="search-field-container">
                            <i data-lucide="search"></i>
                            <input type="text" id="op-search" placeholder="Search users..." oninput="loadOperators(this.value)">
                        </div>
                    </div>
                    <hr style="border: 0; border-top: 1px solid var(--border-color);">
                    <div class="table-responsive">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>User ID</th>
                                    <th>Username</th>
                                    <th>Operational Access</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody id="operators-table-body">
                                <tr><td colspan="4" class="no-data-cell">Loading users...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;
    lucide.createIcons();
    loadOperators();
}

async function loadOperators(search = '') {
    try {
        const res = await fetch(`/api/users?search=${encodeURIComponent(search)}`);
        const users = await res.json();
        currentUsers = users; // cache it
        
        const body = document.getElementById('operators-table-body');
        body.innerHTML = '';
        
        if (users.length > 0) {
            users.forEach(u => {
                const username = escapeHtml(u.username);
                const roleClass = u.role === 'Admin' ? 'badge-danger' : 'badge-success';
                const isSelf = currentUser.username === u.username;
                
                let actionBtnHTML = `
                    <button class="btn btn-danger" style="padding: 6px 12px; font-size: 12px; border-radius: 6px;" onclick="deleteOperator(${u.user_id})">
                        <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i> Delete
                    </button>
                `;
                
                if (isSelf) {
                    actionBtnHTML = `<span class="badge badge-info"><i data-lucide="user" style="width:12px; height:12px; margin-right:4px;"></i> Active Session</span>`;
                }

                body.innerHTML += `
                    <tr>
                        <td><span class="text-muted">#${u.user_id}</span></td>
                        <td><strong>${username}</strong></td>
                        <td><span class="badge ${roleClass}">${u.role}</span></td>
                        <td>${actionBtnHTML}</td>
                    </tr>
                `;
            });
            lucide.createIcons();
        } else {
            body.innerHTML = `<tr><td colspan="4" class="no-data-cell">No operator accounts found.</td></tr>`;
        }
    } catch (e) {
        showAlert('Failed to load operator accounts.', false);
    }
}

async function saveOperator(e) {
    e.preventDefault();
    const username = document.getElementById('op-username').value.trim();
    const password = document.getElementById('op-password').value;
    const role = document.getElementById('op-role').value;

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, role })
        });
        
        const data = await res.json();
        if (res.ok) {
            showAlert(`Operator account '${escapeHtml(username)}' created successfully.`);
            document.getElementById('op-username').value = '';
            document.getElementById('op-password').value = '';
            loadOperators();
        } else {
            showAlert(data.error || 'Username is already taken.', false);
        }
    } catch (err) {
        showAlert('Server connection error.', false);
    }
}

function deleteOperator(id) {
    const u = currentUsers.find(x => x.user_id === id);
    const username = u ? u.username : '';
    showConfirmDialog(
        "Delete Operator Account",
        `Are you sure you want to permanently delete user account '${escapeHtml(username)}'?`,
        async () => {
            try {
                const res = await fetch(`/api/users/${id}`, { method: 'DELETE' });
                if (res.ok) {
                    showAlert(`Operator account '${escapeHtml(username)}' deleted successfully.`);
                    loadOperators();
                } else {
                    showAlert('Failed to delete operator account.', false);
                }
            } catch (e) {
                showAlert('Server connection error.', false);
            }
        }
    );
}
