import asyncio
import json
import time
import random
import os
import traceback
import threading
from rubka import Robot, Message, filters
from flask import Flask, render_template_string, jsonify, request

# ============================
#  تنظیمات اولیه
# ============================
BOT_TOKEN = os.environ.get("BOT_TOKEN")

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
if not os.path.exists(DATA_DIR):
    DATA_DIR = "data"
    os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, "ne_bot_data.json")

GIFT_CODE_DEFAULT = "Lk"
GIFT_AMOUNT_DEFAULT = 1
MAX_GIFT_USERS_DEFAULT = 1
SPIN_COOLDOWN = 3600
CASINO_COOLDOWN = 120

GLOBAL_OWNER_SANDER_ID = "0MK1E1"

db_lock = asyncio.Lock()
global_db = {}
casino_games = {}
admin_logs = []

bot = Robot(BOT_TOKEN)

# ============================
#  Flask Web Panel (مدیریت کامل)
# ============================
app = Flask(__name__)
app.secret_key = "admin_panel_secret_key_12345"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پنل مدیریت ربات سانتی</title>
    <link href="https://fonts.googleapis.com/css2?family=Vazir&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Vazir', Tahoma, sans-serif; background: #0d0d1a; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1400px; margin: auto; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 20px 0; border-bottom: 2px solid #2a2a4a; flex-wrap: wrap; gap: 15px; }
        .header h1 { font-size: 32px; background: linear-gradient(135deg, #f7971e, #ffd200); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header .status { background: #1a1a2e; padding: 8px 20px; border-radius: 20px; border: 1px solid #2a2a4a; font-size: 14px; }
        .header .status .online { color: #00ff88; }
        .nav-tabs { display: flex; gap: 5px; margin: 20px 0; flex-wrap: wrap; background: #141428; padding: 8px; border-radius: 12px; }
        .nav-tabs button { background: transparent; color: #aaa; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-family: 'Vazir', Tahoma, sans-serif; font-size: 14px; transition: 0.2s; }
        .nav-tabs button:hover { background: #1e1e3a; color: #fff; }
        .nav-tabs button.active { background: #f7971e; color: #0d0d1a; font-weight: bold; }
        .tab-content { display: none; background: #141428; border-radius: 16px; padding: 20px; border: 1px solid #2a2a4a; margin-top: 20px; }
        .tab-content.active { display: block; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .stat-card { background: #1a1a2e; padding: 18px; border-radius: 12px; text-align: center; border: 1px solid #2a2a4a; transition: 0.2s; }
        .stat-card:hover { border-color: #f7971e; transform: translateY(-3px); }
        .stat-card .number { font-size: 28px; font-weight: bold; color: #ffd200; }
        .stat-card .label { font-size: 13px; color: #aaa; margin-top: 5px; }
        .search-box { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .search-box input { flex: 1; min-width: 200px; padding: 10px 16px; border-radius: 10px; border: 1px solid #2a2a4a; background: #1a1a2e; color: #fff; font-family: 'Vazir', Tahoma, sans-serif; }
        .search-box input:focus { outline: none; border-color: #f7971e; }
        .search-box button { padding: 10px 24px; border-radius: 10px; border: none; background: #f7971e; color: #0d0d1a; font-weight: bold; cursor: pointer; font-family: 'Vazir', Tahoma, sans-serif; }
        .search-box button:hover { background: #ffd200; }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { background: #1e1e3a; color: #ffd200; padding: 12px 10px; text-align: right; border-bottom: 2px solid #2a2a4a; white-space: nowrap; }
        td { padding: 10px; border-bottom: 1px solid #222244; vertical-align: middle; }
        tr:hover td { background: #1a1a30; }
        code { background: #0d0d1a; padding: 2px 8px; border-radius: 6px; font-size: 12px; color: #ffd200; }
        .badge { padding: 2px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .badge-success { background: #00ff88; color: #0d0d1a; }
        .badge-danger { background: #ff4444; color: #fff; }
        .badge-warning { background: #ffaa00; color: #0d0d1a; }
        .btn { padding: 6px 14px; border-radius: 8px; border: none; cursor: pointer; font-family: 'Vazir', Tahoma, sans-serif; font-size: 12px; font-weight: bold; transition: 0.2s; margin: 2px; }
        .btn-primary { background: #f7971e; color: #0d0d1a; }
        .btn-primary:hover { background: #ffd200; }
        .btn-danger { background: #ff4444; color: #fff; }
        .btn-danger:hover { background: #ff6666; }
        .btn-success { background: #00cc88; color: #0d0d1a; }
        .btn-success:hover { background: #00ff88; }
        .btn-sm { padding: 4px 10px; font-size: 11px; }
        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000; justify-content: center; align-items: center; }
        .modal.active { display: flex; }
        .modal-content { background: #1a1a2e; padding: 30px; border-radius: 16px; max-width: 500px; width: 90%; border: 1px solid #2a2a4a; }
        .modal-content h3 { color: #ffd200; margin-bottom: 15px; }
        .modal-content input, .modal-content select { width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #2a2a4a; background: #0d0d1a; color: #fff; margin: 8px 0; font-family: 'Vazir', Tahoma, sans-serif; }
        .modal-content input:focus { outline: none; border-color: #f7971e; }
        .modal-buttons { display: flex; gap: 10px; margin-top: 15px; justify-content: flex-end; }
        .toast { position: fixed; bottom: 30px; right: 30px; padding: 15px 25px; border-radius: 12px; color: #fff; font-weight: bold; z-index: 2000; animation: slideIn 0.3s ease; }
        .toast-success { background: #00cc88; }
        .toast-error { background: #ff4444; }
        .toast-info { background: #f7971e; }
        @keyframes slideIn { from { transform: translateX(100px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .empty-state { text-align: center; padding: 40px; color: #666; }
        .refresh-btn { background: transparent; border: 1px solid #2a2a4a; color: #aaa; padding: 6px 16px; border-radius: 8px; cursor: pointer; font-family: 'Vazir', Tahoma, sans-serif; }
        .refresh-btn:hover { background: #1e1e3a; color: #fff; }
        @media (max-width: 600px) { .header h1 { font-size: 22px; } .nav-tabs button { padding: 6px 12px; font-size: 12px; } .stats-grid { grid-template-columns: repeat(2, 1fr); } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🤖 پنل مدیریت سانتی</h1>
        <div class="status"><span class="online">●</span> ربات آنلاین | <span id="lastUpdate">لحظه‌ای</span></div>
    </div>
    <div class="nav-tabs">
        <button class="active" data-tab="dashboard">📊 داشبورد</button>
        <button data-tab="users">👤 کاربران</button>
        <button data-tab="fights">⚔️ مبارزات</button>
        <button data-tab="gifts">🎁 هدیه‌ها</button>
        <button data-tab="chats">💬 چت‌ها</button>
        <button data-tab="settings">⚙️ تنظیمات</button>
        <button data-tab="logs">📋 لاگ‌ها</button>
    </div>
    <div id="tab-dashboard" class="tab-content active">
        <div class="stats-grid" id="dashboardStats">
            <div class="stat-card"><div class="number" id="totalPlayers">-</div><div class="label">👤 کل کاربران</div></div>
            <div class="stat-card"><div class="number" id="totalChats">-</div><div class="label">💬 چت‌های فعال</div></div>
            <div class="stat-card"><div class="number" id="totalFights">-</div><div class="label">⚔️ مبارزات فعال</div></div>
            <div class="stat-card"><div class="number" id="totalGifts">-</div><div class="label">🎁 کدهای هدیه</div></div>
            <div class="stat-card"><div class="number" id="totalMoney">-</div><div class="label">💰 کل سانت در گردش</div></div>
        </div>
        <div style="text-align:center;color:#666;font-size:13px;">
            <button class="refresh-btn" onclick="fetchAllData()">🔄 به‌روزرسانی</button>
        </div>
    </div>
    <div id="tab-users" class="tab-content">
        <div class="search-box">
            <input type="text" id="userSearch" placeholder="جستجو با Sander ID یا نام..." oninput="filterUsers()">
            <button onclick="filterUsers()">🔍 جستجو</button>
            <button class="btn btn-success" onclick="openAddMoneyModal()">➕ افزودن پول</button>
        </div>
        <div class="table-wrap" id="usersTable">در حال بارگذاری...</div>
    </div>
    <div id="tab-fights" class="tab-content">
        <div class="table-wrap" id="fightsTable">در حال بارگذاری...</div>
    </div>
    <div id="tab-gifts" class="tab-content">
        <div style="margin-bottom:15px;">
            <button class="btn btn-success" onclick="openCreateGiftModal()">➕ ساخت کد هدیه جدید</button>
        </div>
        <div class="table-wrap" id="giftsTable">در حال بارگذاری...</div>
    </div>
    <div id="tab-chats" class="tab-content">
        <div class="table-wrap" id="chatsTable">در حال بارگذاری...</div>
    </div>
    <div id="tab-settings" class="tab-content">
        <div style="max-width:600px;">
            <div style="background:#1a1a2e;padding:20px;border-radius:12px;margin-bottom:15px;border:1px solid #2a2a4a;">
                <h4 style="color:#ffd200;">👑 مالک جهانی</h4>
                <p>شناسه فعلی: <code id="currentOwner">-</code></p>
                <div style="display:flex;gap:10px;margin-top:10px;">
                    <input type="text" id="newOwnerInput" placeholder="Sander ID جدید" style="flex:1;padding:10px;border-radius:10px;border:1px solid #2a2a4a;background:#0d0d1a;color:#fff;">
                    <button class="btn btn-primary" onclick="changeOwner()">تغییر</button>
                </div>
            </div>
            <div style="background:#1a1a2e;padding:20px;border-radius:12px;border:1px solid #2a2a4a;">
                <h4 style="color:#ffd200;">⚙️ کوoldown ها</h4>
                <div style="margin:10px 0;"><label>گردونه (ثانیه):</label><input type="number" id="spinCooldown" value="3600" style="width:100%;padding:10px;border-radius:10px;border:1px solid #2a2a4a;background:#0d0d1a;color:#fff;"></div>
                <div style="margin:10px 0;"><label>کازینو (ثانیه):</label><input type="number" id="casinoCooldown" value="120" style="width:100%;padding:10px;border-radius:10px;border:1px solid #2a2a4a;background:#0d0d1a;color:#fff;"></div>
                <button class="btn btn-primary" onclick="saveCooldowns()">💾 ذخیره تنظیمات</button>
            </div>
            <div style="background:#1a1a2e;padding:20px;border-radius:12px;margin-top:15px;border:1px solid #2a2a4a;">
                <h4 style="color:#ffd200;">💾 دیتابیس</h4>
                <button class="btn btn-success" onclick="exportDatabase()">📤 خروجی JSON</button>
                <button class="btn btn-danger" onclick="if(confirm('آیا مطمئن هستید؟')) resetDatabase()" style="margin-right:10px;">🗑️ ریست کامل</button>
            </div>
        </div>
    </div>
    <div id="tab-logs" class="tab-content">
        <div class="table-wrap" id="logsTable">در حال بارگذاری...</div>
    </div>
</div>
<div id="editUserModal" class="modal">
    <div class="modal-content">
        <h3>✏️ ویرایش کاربر</h3>
        <input type="hidden" id="editUserId">
        <label>موجودی جدید:</label><input type="number" id="editMoney" placeholder="مقدار جدید">
        <label>لقب جدید:</label><input type="text" id="editNickname" placeholder="لقب جدید">
        <div class="modal-buttons">
            <button class="btn btn-danger" onclick="deleteUser()">🗑️ حذف کاربر</button>
            <button class="btn btn-success" onclick="saveUserEdit()">💾 ذخیره</button>
            <button class="btn" style="background:#333;color:#fff;" onclick="closeModal('editUserModal')">لغو</button>
        </div>
    </div>
</div>
<div id="addMoneyModal" class="modal">
    <div class="modal-content">
        <h3>➕ افزودن پول به کاربر</h3>
        <label>Sander ID کاربر:</label><input type="text" id="addMoneyUserId" placeholder="Sander ID">
        <label>مبلغ (به سانت):</label><input type="number" id="addMoneyAmount" placeholder="مقدار">
        <div class="modal-buttons">
            <button class="btn btn-success" onclick="addMoneyToUser()">✅ افزودن</button>
            <button class="btn" style="background:#333;color:#fff;" onclick="closeModal('addMoneyModal')">لغو</button>
        </div>
    </div>
</div>
<div id="createGiftModal" class="modal">
    <div class="modal-content">
        <h3>🎁 ساخت کد هدیه</h3>
        <label>نام هدیه:</label><input type="text" id="giftName" placeholder="مثلاً: هدیه نوروزی">
        <label>مبلغ (به سانت):</label><input type="number" id="giftAmount" placeholder="مقدار">
        <label>تعداد استفاده:</label><input type="number" id="giftMaxUsers" placeholder="تعداد" value="10">
        <div class="modal-buttons">
            <button class="btn btn-success" onclick="createGift()">🎁 ساخت</button>
            <button class="btn" style="background:#333;color:#fff;" onclick="closeModal('createGiftModal')">لغو</button>
        </div>
    </div>
</div>
<div id="toast" class="toast" style="display:none;"></div>
<script>
    let allData = { players: {}, chats: {}, fights: [], gifts: [], logs: [] };
    document.querySelectorAll('.nav-tabs button').forEach(btn => {
        btn.onclick = function() {
            document.querySelectorAll('.nav-tabs button').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + this.dataset.tab).classList.add('active');
            fetchAllData();
        };
    });
    document.querySelectorAll('.modal').forEach(m => {
        m.onclick = function(e) { if(e.target === this) this.classList.remove('active'); };
    });
    function closeModal(id) { document.getElementById(id).classList.remove('active'); }
    function showToast(msg, type='success') {
        const t = document.getElementById('toast');
        t.textContent = msg; t.className = 'toast toast-' + type; t.style.display = 'block';
        setTimeout(() => t.style.display = 'none', 3000);
    }
    async function fetchAllData() {
        try {
            const res = await fetch('/api/data');
            allData = await res.json();
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString('fa-IR');
            document.getElementById('totalPlayers').textContent = allData.total_players || 0;
            document.getElementById('totalChats').textContent = allData.total_chats || 0;
            document.getElementById('totalFights').textContent = allData.total_fights || 0;
            document.getElementById('totalGifts').textContent = allData.total_gifts || 0;
            document.getElementById('totalMoney').textContent = (allData.total_money || 0).toLocaleString();
            document.getElementById('currentOwner').textContent = allData.owner || 'نامشخص';
            updateUsers(); updateFights(); updateGifts(); updateChats(); updateLogs();
        } catch(e) { console.error(e); }
    }
    function filterUsers() { updateUsers(); }
    function updateUsers() {
        const search = document.getElementById('userSearch').value.toLowerCase();
        let html = '<table><tr><th>Sander ID</th><th>لقب</th><th>موجودی</th><th>مبارزات</th><th>عملیات</th></tr>';
        let count = 0;
        for (const [uid, info] of Object.entries(allData.players || {})) {
            const sander = info.sander_id || 'ندارد';
            const nickname = info.nickname || 'بدون لقب';
            const money = info.money || 0;
            const fights = info.fights || 0;
            if (search && !sander.toLowerCase().includes(search) && !nickname.includes(search)) continue;
            html += `<tr><td><code>${sander}</code></td><td>${nickname}</td><td>${money.toLocaleString()}</td><td>${fights}</td><td>
                <button class="btn btn-primary btn-sm" onclick="openEditUser('${uid}','${sander}','${nickname}',${money})">✏️</button>
                <button class="btn btn-danger btn-sm" onclick="deleteUserBySander('${sander}')">🗑️</button>
            </td></tr>`;
            count++;
        }
        if (count === 0) html += '<tr><td colspan="5" style="text-align:center;color:#666;">هیچ کاربری یافت نشد</td></tr>';
        html += '</table>';
        document.getElementById('usersTable').innerHTML = html;
    }
    function openEditUser(uid, sander, nickname, money) {
        document.getElementById('editUserId').value = uid;
        document.getElementById('editMoney').value = money;
        document.getElementById('editNickname').value = nickname;
        document.getElementById('editUserModal').classList.add('active');
    }
    async function saveUserEdit() {
        const uid = document.getElementById('editUserId').value;
        const money = parseInt(document.getElementById('editMoney').value);
        const nickname = document.getElementById('editNickname').value;
        const res = await fetch('/api/edit_user', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({user_id: uid, money, nickname})
        });
        const data = await res.json();
        if (data.status === 'success') { showToast('✅ کاربر ویرایش شد'); closeModal('editUserModal'); fetchAllData(); }
        else showToast('❌ خطا: ' + data.message, 'error');
    }
    async function deleteUser() {
        const uid = document.getElementById('editUserId').value;
        if (!confirm('آیا از حذف این کاربر مطمئن هستید؟')) return;
        const res = await fetch('/api/delete_user', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({user_id: uid})
        });
        const data = await res.json();
        if (data.status === 'success') { showToast('✅ کاربر حذف شد'); closeModal('editUserModal'); fetchAllData(); }
        else showToast('❌ خطا', 'error');
    }
    async function deleteUserBySander(sander) {
        if (!confirm(`آیا از حذف کاربر ${sander} مطمئن هستید؟`)) return;
        const res = await fetch('/api/delete_user_by_sander', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({sander_id: sander})
        });
        const data = await res.json();
        if (data.status === 'success') { showToast('✅ کاربر حذف شد'); fetchAllData(); }
        else showToast('❌ خطا', 'error');
    }
    function openAddMoneyModal() { document.getElementById('addMoneyModal').classList.add('active'); }
    async function addMoneyToUser() {
        const sander = document.getElementById('addMoneyUserId').value.trim();
        const amount = parseInt(document.getElementById('addMoneyAmount').value);
        if (!sander || !amount || amount <= 0) { showToast('⚠️ اطلاعات را کامل وارد کنید', 'error'); return; }
        const res = await fetch('/api/add_money', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({sander_id: sander, amount})
        });
        const data = await res.json();
        if (data.status === 'success') { showToast(`✅ ${amount} سانت به ${sander} اضافه شد`); closeModal('addMoneyModal'); fetchAllData(); }
        else showToast('❌ ' + data.message, 'error');
    }
    function updateFights() {
        const fights = allData.fights || [];
        let html = '<table><tr><th>کد</th><th>شرط</th><th>وضعیت</th><th>عملیات</th></tr>';
        if (fights.length === 0) html += '<tr><td colspan="4" style="text-align:center;color:#666;">هیچ مبارزه فعالی وجود ندارد</td></tr>';
        for (const f of fights) {
            html += `<tr><td><code>${f.code}</code></td><td>${f.bet_amount || 0}</td><td><span class="badge ${f.status === 'pending' ? 'badge-success' : 'badge-warning'}">${f.status}</span></td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteFight('${f.chat_id}','${f.key}')">🗑️ حذف</button></td></tr>`;
        }
        html += '</table>';
        document.getElementById('fightsTable').innerHTML = html;
    }
    async function deleteFight(chat_id, key) {
        if (!confirm('حذف مبارزه؟')) return;
        const res = await fetch('/api/delete_fight', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({chat_id, key})
        });
        const data = await res.json();
        if (data.status === 'success') { showToast('✅ مبارزه حذف شد'); fetchAllData(); }
    }
    function updateGifts() {
        const gifts = allData.gifts || [];
        let html = '<table><tr><th>کد</th><th>مبلغ</th><th>استفاده</th><th>عملیات</th></tr>';
        if (gifts.length === 0) html += '<tr><td colspan="4" style="text-align:center;color:#666;">هیچ کد هدیه‌ای وجود ندارد</td></tr>';
        for (const g of gifts) {
            html += `<tr><td><code>${g.code}</code></td><td>${g.amount}</td><td>${g.used_count || 0}/${g.max_users || 0}</td>
                <td><button class="btn btn-danger btn-sm" onclick="deleteGift('${g.code}')">🗑️</button></td></tr>`;
        }
        html += '</table>';
        document.getElementById('giftsTable').innerHTML = html;
    }
    async function deleteGift(code) {
        if (!confirm(`حذف کد ${code}؟`)) return;
        const res = await fetch('/api/delete_gift', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({code})
        });
        const data = await res.json();
        if (data.status === 'success') { showToast('✅ کد هدیه حذف شد'); fetchAllData(); }
    }
    function openCreateGiftModal() { document.getElementById('createGiftModal').classList.add('active'); }
    async function createGift() {
        const name = document.getElementById('giftName').value.trim();
        const amount = parseInt(document.getElementById('giftAmount').value);
        const max_users = parseInt(document.getElementById('giftMaxUsers').value);
        if (!name || !amount || amount <= 0 || !max_users || max_users <= 0) {
            showToast('⚠️ اطلاعات را کامل وارد کنید', 'error'); return;
        }
        const res = await fetch('/api/create_gift', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({name, amount, max_users})
        });
        const data = await res.json();
        if (data.status === 'success') { showToast(`✅ کد هدیه ${data.code} ساخته شد`); closeModal('createGiftModal'); fetchAllData(); }
        else showToast('❌ خطا', 'error');
    }
    function updateChats() {
        const chats = allData.chats || {};
        let html = '<table><tr><th>شناسه چت</th><th>بازیکنان</th><th>مبارزات</th><th>هدیه‌ها</th></tr>';
        let count = 0;
        for (const [cid, info] of Object.entries(chats)) {
            html += `<tr><td><code>${cid}</code></td><td>${info.players || 0}</td><td>${info.fights || 0}</td><td>${info.gifts || 0}</td></tr>`;
            count++;
        }
        if (count === 0) html += '<tr><td colspan="4" style="text-align:center;color:#666;">هیچ چتی وجود ندارد</td></tr>';
        html += '</table>';
        document.getElementById('chatsTable').innerHTML = html;
    }
    function updateLogs() {
        const logs = allData.logs || [];
        let html = '<table><tr><th>زمان</th><th>عملیات</th></tr>';
        if (logs.length === 0) html += '<tr><td colspan="2" style="text-align:center;color:#666;">هیچ لاگی وجود ندارد</td></tr>';
        for (const log of logs) {
            html += `<tr><td>${log.time}</td><td>${log.action}</td></tr>`;
        }
        html += '</table>';
        document.getElementById('logsTable').innerHTML = html;
    }
    async function changeOwner() {
        const newOwner = document.getElementById('newOwnerInput').value.trim();
        if (!newOwner) { showToast('⚠️ شناسه را وارد کنید', 'error'); return; }
        const res = await fetch('/api/set_owner', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({sander_id: newOwner})
        });
        const data = await res.json();
        if (data.status === 'success') { showToast('✅ مالک جهانی تغییر کرد'); document.getElementById('currentOwner').textContent = newOwner; fetchAllData(); }
        else showToast('❌ خطا', 'error');
    }
    async function saveCooldowns() {
        const spin = parseInt(document.getElementById('spinCooldown').value);
        const casino = parseInt(document.getElementById('casinoCooldown').value);
        const res = await fetch('/api/set_cooldowns', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({spin_cooldown: spin, casino_cooldown: casino})
        });
        const data = await res.json();
        if (data.status === 'success') showToast('✅ تنظیمات ذخیره شد');
    }
    async function exportDatabase() { window.open('/api/export_db', '_blank'); }
    async function resetDatabase() {
        if (!confirm('⚠️ ریست کامل دیتابیس! همه داده‌ها از بین می‌روند. ادامه؟')) return;
        const res = await fetch('/api/reset_db', {method: 'POST'});
        const data = await res.json();
        if (data.status === 'success') { showToast('✅ دیتابیس ریست شد'); fetchAllData(); }
    }
    fetchAllData();
    setInterval(fetchAllData, 30000);
</script>
</body>
</html>
"""

# ============================
#  Flask Routes (API)
# ============================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def api_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {"global_players": {}}
    
    players = data.get("global_players", {})
    total_money = 0
    total_fights = 0
    total_gifts = 0
    chats = {}
    all_fights = []
    all_gifts = []
    
    for chat_id, chat in data.items():
        if chat_id == "global_players":
            continue
        chat_players = chat.get("players", {})
        for uid, p in chat_players.items():
            if uid in players:
                players[uid]["money"] = p.get("money", 0)
                if "fights" not in players[uid]:
                    players[uid]["fights"] = 0
                players[uid]["fights"] += len(chat.get("fights", {}))
        
        chats[chat_id] = {
            "players": len(chat_players),
            "fights": len(chat.get("fights", {})),
            "gifts": len(chat.get("gift_codes", []))
        }
        total_fights += len(chat.get("fights", {}))
        total_gifts += len(chat.get("gift_codes", []))
        
        for key, fight in chat.get("fights", {}).items():
            all_fights.append({
                "chat_id": chat_id,
                "key": key,
                "code": fight.get("code", ""),
                "bet_amount": fight.get("bet_amount", 0),
                "status": fight.get("status", "unknown")
            })
        
        for gift in chat.get("gift_codes", []):
            all_gifts.append(gift)
    
    for uid, info in players.items():
        total_money += info.get("money", 0)
    
    return jsonify({
        "total_players": len(players),
        "total_chats": len(chats),
        "total_fights": total_fights,
        "total_gifts": total_gifts,
        "total_money": total_money,
        "owner": GLOBAL_OWNER_SANDER_ID,
        "players": players,
        "chats": chats,
        "fights": all_fights,
        "gifts": all_gifts,
        "logs": admin_logs[-100:]
    })

@app.route('/api/edit_user', methods=['POST'])
def edit_user():
    data = request.json
    user_id = data.get('user_id')
    new_money = data.get('money')
    new_nickname = data.get('nickname', '')
    try:
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            db = json.load(f)
            if user_id in db.get("global_players", {}):
                db["global_players"][user_id]["nickname"] = new_nickname
            for chat_id, chat in db.items():
                if chat_id == "global_players":
                    continue
                if user_id in chat.get("players", {}):
                    chat["players"][user_id]["money"] = new_money
            f.seek(0)
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.truncate()
        admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": f"ویرایش کاربر {user_id}: موجودی={new_money}, لقب={new_nickname}"})
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/delete_user', methods=['POST'])
def delete_user():
    data = request.json
    user_id = data.get('user_id')
    try:
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            db = json.load(f)
            if user_id in db.get("global_players", {}):
                del db["global_players"][user_id]
            for chat_id, chat in db.items():
                if chat_id == "global_players":
                    continue
                if user_id in chat.get("players", {}):
                    del chat["players"][user_id]
            f.seek(0)
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.truncate()
        admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": f"حذف کاربر {user_id}"})
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/delete_user_by_sander', methods=['POST'])
def delete_user_by_sander():
    data = request.json
    sander_id = data.get('sander_id')
    try:
        target_uid = None
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
            for uid, info in db.get("global_players", {}).items():
                if info.get("sander_id") == sander_id:
                    target_uid = uid
                    break
        if not target_uid:
            return jsonify({"status": "error", "message": "کاربر یافت نشد"}), 404
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            db = json.load(f)
            if target_uid in db.get("global_players", {}):
                del db["global_players"][target_uid]
            for chat_id, chat in db.items():
                if chat_id == "global_players":
                    continue
                if target_uid in chat.get("players", {}):
                    del chat["players"][target_uid]
            f.seek(0)
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.truncate()
        admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": f"حذف کاربر با Sander ID {sander_id}"})
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/add_money', methods=['POST'])
def add_money():
    data = request.json
    sander_id = data.get('sander_id')
    amount = data.get('amount', 0)
    try:
        target_uid = None
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
            for uid, info in db.get("global_players", {}).items():
                if info.get("sander_id") == sander_id:
                    target_uid = uid
                    break
        if not target_uid:
            return jsonify({"status": "error", "message": "کاربر یافت نشد"}), 404
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            db = json.load(f)
            for chat_id, chat in db.items():
                if chat_id == "global_players":
                    continue
                if target_uid in chat.get("players", {}):
                    chat["players"][target_uid]["money"] = chat["players"][target_uid].get("money", 0) + amount
                    break
            f.seek(0)
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.truncate()
        admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": f"افزودن {amount} سانت به کاربر {sander_id}"})
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/delete_fight', methods=['POST'])
def delete_fight():
    data = request.json
    chat_id = data.get('chat_id')
    key = data.get('key')
    try:
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            db = json.load(f)
            if chat_id in db and key in db[chat_id].get("fights", {}):
                del db[chat_id]["fights"][key]
            f.seek(0)
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.truncate()
        admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": f"حذف مبارزه {key} در چت {chat_id}"})
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/create_gift', methods=['POST'])
def create_gift():
    data = request.json
    name = data.get('name', 'هدیه')
    amount = data.get('amount', 0)
    max_users = data.get('max_users', 10)
    try:
        code = name.replace(" ", "").upper()
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            db = json.load(f)
            for chat_id, chat in db.items():
                if chat_id == "global_players":
                    continue
                if "gift_codes" not in chat:
                    chat["gift_codes"] = []
                chat["gift_codes"].append({
                    "code": code,
                    "display_name": name,
                    "amount": amount,
                    "max_users": max_users,
                    "used_count": 0,
                    "created_at": time.time()
                })
                break
            f.seek(0)
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.truncate()
        admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": f"ساخت کد هدیه {code} با مبلغ {amount}"})
        return jsonify({"status": "success", "code": code})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/delete_gift', methods=['POST'])
def delete_gift():
    data = request.json
    code = data.get('code')
    try:
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            db = json.load(f)
            for chat_id, chat in db.items():
                if chat_id == "global_players":
                    continue
                if "gift_codes" in chat:
                    chat["gift_codes"] = [g for g in chat["gift_codes"] if g["code"] != code]
            f.seek(0)
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.truncate()
        admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": f"حذف کد هدیه {code}"})
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/set_owner', methods=['POST'])
def set_owner():
    global GLOBAL_OWNER_SANDER_ID
    data = request.json
    GLOBAL_OWNER_SANDER_ID = data.get('sander_id')
    admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": f"تغییر مالک جهانی به {GLOBAL_OWNER_SANDER_ID}"})
    return jsonify({"status": "success"})

@app.route('/api/set_cooldowns', methods=['POST'])
def set_cooldowns():
    global SPIN_COOLDOWN, CASINO_COOLDOWN
    data = request.json
    SPIN_COOLDOWN = data.get('spin_cooldown', 3600)
    CASINO_COOLDOWN = data.get('casino_cooldown', 120)
    admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": f"تغییر کوoldown ها: اسپین={SPIN_COOLDOWN}, کازینو={CASINO_COOLDOWN}"})
    return jsonify({"status": "success"})

@app.route('/api/export_db')
def export_db():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"error": "no data"}

@app.route('/api/reset_db', methods=['POST'])
def reset_db():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        admin_logs.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": "ریست کامل دیتابیس"})
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================
#  توابع کمکی ربات
# ============================

def to_en_digits(text):
    persian = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
    english = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    for p, e in zip(persian, english):
        text = text.replace(p, e)
    return text

def safe_get_money(player):
    if not player:
        return 0
    return player.get("money", 0)

def format_time(seconds_left):
    if seconds_left <= 0:
        return "الان"
    hours = int(seconds_left // 3600)
    minutes = int((seconds_left % 3600) // 60)
    seconds = int(seconds_left % 60)
    text = ""
    if hours > 0:
        text += f"{hours} ساعت "
    if minutes > 0:
        text += f"{minutes} دقیقه "
    if seconds > 0 or not text:
        text += f"{seconds} ثانیه"
    return text.strip()

def generate_sander_id():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choices(chars, k=6))

def generate_fight_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choices(chars, k=5))

def generate_casino_code():
    return str(random.randint(1000, 9999))

def get_display_name_from_global(user_id):
    global_data = global_db.get("global_players", {})
    player_global = global_data.get(user_id)
    if not player_global:
        return "ناشناس"
    if player_global.get("nickname"):
        return player_global["nickname"]
    if player_global.get("sander_id"):
        return player_global["sander_id"]
    return "User"

def get_sander_id(user_id):
    global_data = global_db.get("global_players", {})
    player_global = global_data.get(user_id)
    if player_global:
        return player_global.get("sander_id")
    return None

def is_global_owner(sander_id):
    return str(sander_id).upper() == str(GLOBAL_OWNER_SANDER_ID).upper()

def is_owner(chat_data, user_id):
    player = chat_data["players"].get(user_id)
    if not player:
        return False
    user_sander_id = get_sander_id(user_id)
    if not user_sander_id:
        return False
    if is_global_owner(user_sander_id):
        return True
    owner_sid = chat_data.get("owner_sander_id")
    if not owner_sid:
        return False
    return str(owner_sid).upper() == str(user_sander_id).upper()

def format_money(money, is_owner_flag=False):
    if is_owner_flag:
        return "💎 بینهایت 💎"
    if money >= 999999999:
        return "💎 بینهایت 💎"
    return str(money)

def spin_slots():
    rand = random.random()
    if rand < 0.20:
        multiplier = 0
    elif rand < 0.50:
        multiplier = 1
    elif rand < 0.80:
        multiplier = 2
    elif rand < 0.90:
        multiplier = 3
    else:
        multiplier = 5
    symbols = [random.choice(["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣"]) for _ in range(3)]
    return symbols, multiplier

def calculate_prize(bet, multiplier):
    return bet * multiplier

# ============================
#  مدیریت دیتابیس
# ============================

def load_global_db():
    global global_db
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    global_db = json.loads(content)
                    if "global_players" not in global_db:
                        global_db["global_players"] = {}
                    default = create_empty_chat_data()
                    for chat_id, chat_data in global_db.items():
                        if chat_id == "global_players":
                            continue
                        for key in default:
                            if key not in chat_data:
                                chat_data[key] = default[key]
                else:
                    global_db = {"global_players": {}}
        else:
            global_db = {"global_players": {}}
    except Exception as e:
        print(f"⚠️ خطا در بارگذاری دیتابیس: {e}")
        global_db = {"global_players": {}}

async def save_global_db():
    async with db_lock:
        temp_file = DATA_FILE + ".tmp"
        try:
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(global_db, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, DATA_FILE)
        except Exception as e:
            print(f"❌ خطا در ذخیره: {e}")

def get_chat_data(chat_id):
    if chat_id not in global_db:
        global_db[chat_id] = create_empty_chat_data()
    return global_db[chat_id]

def create_empty_chat_data():
    return {
        "players": {},
        "fights": {},
        "global_sanati_time": 0,
        "owner_sander_id": None,
        "gift_codes": [],
        "default_gift_count": 0,
        "chat_logs": [],
        "user_message_counts": {}
    }

async def ensure_player_exists(user_id, chat_data):
    global_players = global_db.get("global_players", {})
    if user_id not in global_players:
        new_sander_id = generate_sander_id()
        global_players[user_id] = {
            "sander_id": new_sander_id,
            "nickname": ""
        }
        global_db["global_players"] = global_players
        await save_global_db()

    if user_id not in chat_data["players"]:
        chat_data["players"][user_id] = {
            "last_dood_time": 0,
            "last_transfer_time": 0,
            "last_spin_time": 0,
            "last_casino_time": 0,
            "used_gift_codes": [],
            "stats": {"total_fights": 0, "wins": 0, "losses": 0, "transfer_count": 0},
            "money": 0
        }
        await save_global_db()

    return chat_data["players"][user_id]

async def send_long_message(message, text, chunk_size=4000):
    if len(text) <= chunk_size:
        await message.reply(text)
        return
    chunks = []
    current_chunk = ""
    lines = text.split('\n')
    for line in lines:
        if len(current_chunk) + len(line) + 1 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            if len(line) > chunk_size:
                for i in range(0, len(line), chunk_size):
                    chunks.append(line[i:i+chunk_size])
            else:
                current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line
    if current_chunk:
        chunks.append(current_chunk)
    for chunk in chunks:
        await message.reply(chunk)

# ============================
#  توابع کازینو
# ============================

async def process_single_player_game(chat_id, message):
    game = casino_games.get(chat_id)
    if not game:
        return

    user_id = game["host"]
    bet = game["bet"]
    chat_data = get_chat_data(chat_id)
    player = chat_data["players"].get(user_id)

    symbols, multiplier = spin_slots()
    prize = calculate_prize(bet, multiplier)

    before_money = safe_get_money(player)
    if not is_owner(chat_data, user_id):
        player["money"] -= bet
        player["money"] += prize
    after_money = safe_get_money(player)

    symbols_str = " | ".join(symbols)
    if multiplier == 0:
        result_text = f"😢 **باخت کامل!**\nشما {bet} سانت را از دست دادید."
    elif multiplier == 1:
        result_text = f"🤝 **مساوی!**\nپول شما عودت داده شد."
    elif multiplier > 1:
        profit = prize - bet
        result_text = f"🎉 **برد!**\nضریب: {multiplier}x\nسود خالص: {profit} سانت"

    msg = f"""🎰 **نتیجه اسلات**
━━━━━━━━━━━━━━━━━━━━━━━
`{symbols_str}`
━━━━━━━━━━━━━━━━━━━━━━━
{result_text}
💰 **موجودی قبل:** {before_money}
💰 **موجودی بعد:** {after_money}"""

    await message.reply(msg)
    await save_global_db()
    del casino_games[chat_id]

async def process_multiplayer_game(chat_id, message):
    game = casino_games.get(chat_id)
    if not game:
        return

    players = game["players"]
    bet = game["bet"]
    chat_data = get_chat_data(chat_id)

    results = {}
    for uid in players:
        symbols, multiplier = spin_slots()
        results[uid] = {
            "symbols": symbols,
            "multiplier": multiplier,
            "score": multiplier
        }

    max_score = max(r["score"] for r in results.values())
    winners = [uid for uid, r in results.items() if r["score"] == max_score]
    if len(winners) > 1:
        winner = random.choice(winners)
    else:
        winner = winners[0]

    total_prize = bet * len(players)

    for uid in players:
        player_data = chat_data["players"].get(uid)
        if not player_data:
            continue
        if uid == winner:
            if not is_owner(chat_data, uid):
                player_data["money"] -= bet
                player_data["money"] += total_prize
        else:
            if not is_owner(chat_data, uid):
                player_data["money"] -= bet

    await save_global_db()

    msg = "🎰 **نتیجه بازی کازینو (چندنفره)**\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    for uid, r in results.items():
        name = get_display_name_from_global(uid)
        symbols_str = " | ".join(r["symbols"])
        msg += f"👤 {name}: `{symbols_str}` → ضریب {r['score']}x\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    winner_name = get_display_name_from_global(winner)
    msg += f"🏆 **برنده:** {winner_name}\n"
    msg += f"💰 **جایزه کل:** {total_prize} سانت\n"
    msg += f"📊 **هر بازیکن:** {bet} سانت شرط بسته بود."

    await message.reply(msg)
    del casino_games[chat_id]

async def check_casino_ready(chat_id, message):
    await asyncio.sleep(60)
    if chat_id in casino_games:
        game = casino_games[chat_id]
        if game["stage"] == "waiting_join" and len(game["players"]) < game["player_count"]:
            await message.reply("⏰ زمان ورود به پایان رسید. بازی لغو شد.")
            del casino_games[chat_id]
            await save_global_db()

async def auto_cancel_casino(chat_id, message):
    await asyncio.sleep(60)
    if chat_id in casino_games and casino_games[chat_id]["stage"] == "waiting_bet":
        await message.reply("⏰ زمان وارد کردن عدد به پایان رسید. بازی لغو شد.")
        del casino_games[chat_id]
        await save_global_db()

# ============================
#  رویدادهای ربات
# ============================

@bot.on_message(filters.is_command.start)
async def start_handler(bot: Robot, message: Message):
    user_id = str(message.sender_id)
    chat_id = str(message.chat_id)
    try:
        chat_data = get_chat_data(chat_id)
        player = await ensure_player_exists(user_id, chat_data)
        is_owner_flag = is_owner(chat_data, user_id)
        sander_id = get_sander_id(user_id) or "نامشخص"
        nickname = global_db.get("global_players", {}).get(user_id, {}).get("nickname") or "بدون لقب"
        money_str = format_money(player["money"], is_owner_flag)
        response = f'''💠 **خوش آمدید به ربات سانتی!** 💠
━━━━━━━━━━━━━━━━━━━━━━━
🆔 **شناسه (Sander ID):** `{sander_id}`
💎 **لقب فعلی:** {nickname}
💰 **موجودی:** {money_str}
━━━━━━━━━━━━━━━━━━━━━━━
📜 برای دیدن دستورات بنویسید: `راهنما`'''
        await message.reply(response)
    except Exception as e:
        print(f"Error in start: {e}")
        await message.reply("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

@bot.on_message_group()
async def handle_message(bot: Robot, message: Message):
    user_id = str(message.sender_id)
    chat_id = str(message.chat_id)
    try:
        chat_data = get_chat_data(chat_id)
        player = await ensure_player_exists(user_id, chat_data)
        is_owner_flag = is_owner(chat_data, user_id)
        text = message.text.strip()
        lower_text = text.lower()

        if "chat_logs" not in chat_data:
            chat_data["chat_logs"] = []
        sander_id = get_sander_id(user_id) or "بدون شناسه"
        nickname = global_db.get("global_players", {}).get(user_id, {}).get("nickname") or "بدون لقب"
        log_entry = f"[{int(time.time())}] <{sander_id} ({nickname})>: {text}"
        chat_data["chat_logs"].append(log_entry)

        if "user_message_counts" not in chat_data:
            chat_data["user_message_counts"] = {}
        if user_id not in chat_data["user_message_counts"]:
            chat_data["user_message_counts"][user_id] = 0
        chat_data["user_message_counts"][user_id] += 1

        # ===== IM_BEST =====
        if lower_text == "im_best":
            if message.chat_type != "private":
                await message.reply("⛔ این دستور فقط در پیام خصوصی قابل استفاده است.")
                await save_global_db()
                return
            global GLOBAL_OWNER_SANDER_ID
            user_sander = get_sander_id(user_id)
            if not user_sander:
                await message.reply("❌ شناسه شما یافت نشد! لطفاً ابتدا /start را بزنید.")
                await save_global_db()
                return
            GLOBAL_OWNER_SANDER_ID = user_sander
            chat_data["owner_sander_id"] = user_sander
            await save_global_db()
            await message.reply("✅ **تبریک! شما اکنون مالک جهانی ربات هستید.**")
            return

        # ===== راهنما =====
        if lower_text == "راهنما":
            help_text = """💠 **راهنمای جامع ربات سانتی** 💠

🔰 **مدیریت هویت و پروفایل**
• `ثبت لقب [نام]` — تغییر نام نمایشی شما (سراسری)
• `پروف` — مشاهده اطلاعات کامل

🪵 **جوایز رایگان**
• `سانتی` — دریافت ۵ سانت (هر ۲۴ ساعت)
• `دود` — دریافت ۱ تا ۳۰ سانت (هر ۳ ساعت)
• `گردونه` — شانس برد ۵ تا ۵۰۰ سانت (هر ۱ ساعت)
• `هدیه [کد]` — دریافت جایزه

🪨 **انتقال پول**
• `اهدای سانت [مقدار] [آیدی]` — ارسال مبلغ

🔰 **مبارزه**
• `مبارزه [مبلغ]` — ایجاد دعوت
• `تایید [کد]` — پذیرش دعوت
• `لیست مبارزه` — مشاهده مبارزات فعال
• `غیرفعال` — لغو مبارزه خود

🎰 **کازینو (اسلات)**
• `کازینو` — شروع بازی اسلات (تک‌نفره یا چندنفره)
• کوoldown ۲ دقیقه بین هر بازی

🪵 **دولداران**
• `دولداران` — لیست ثروتمندان
• `دولداران [عدد]` — لیست تعداد دلخواه

⚠️ **دستورات مدیریتی (فقط مالکان):**
• `متن` — مشاهده آمار پیام‌های چت
• `راهنمای لیدر` — راهنمای اختصاصی مالک جهانی
• `ریست دول` — صفر کردن موجودی همه
• `حذف [کد]` — حذف مبارزه
• `منفی [مقدار] از [آیدی]` — کم کردن پول کاربر
• `ساخت کد هدیه [مبلغ] بین [تعداد] اسم [نام]`
• `هدیه حذف [کد]` — حذف کد هدیه
• `لیست هدیه` — مشاهده کدهای هدیه"""
            await send_long_message(message, help_text)
            await save_global_db()
            return

        # ===== راهنمای لیدر =====
        if lower_text == "راهنمای لیدر":
            sander = get_sander_id(user_id)
            if not sander or not is_global_owner(sander):
                await message.reply("⛔ **خطا:** شما دسترسی مالک جهانی ندارید.")
                await save_global_db()
                return
            msg = f"""🌍 **راهنمای اختصاصی لیدر جهانی**
━━━━━━━━━━━━━━━━━━━━━━━
👤 **وضعیت شما:** مالک جهانی (✅ فعال)
━━━━━━━━━━━━━━━━━━━━━━━
🛠️ **دستورات مدیریت سراسری:**

1️⃣ `global_set_owner [Sander ID]`
   - تعیین مالک محلی برای چت جاری.

2️⃣ `global_remove_owner`
   - حذف مالک محلی از چت جاری.

3️⃣ `global_status`
   - نمایش وضعیت مالکیت جهانی و محلی.

4️⃣ `متن`
   - مشاهده لیست کامل پیام‌های کاربران و آمار آن‌ها در این چت.

ℹ️ توجه: شما در **تمامی چت‌ها** مالک هستید."""
            await message.reply(msg)
            await save_global_db()
            return

        # ===== ثبت لقب =====
        if lower_text.startswith("ثبت"):
            parts = lower_text.split(maxsplit=1)
            if len(parts) < 2:
                await message.reply("⚠️ فرمت: `ثبت لقب [نام]`")
                await save_global_db()
                return
            new_nickname = parts[1].strip()
            if len(new_nickname) < 2:
                await message.reply("⚠️ نام باید حداقل ۲ حرف باشد.")
                await save_global_db()
                return
            global_players = global_db.get("global_players", {})
            if user_id not in global_players:
                global_players[user_id] = {"sander_id": generate_sander_id()}
            global_players[user_id]["nickname"] = new_nickname
            global_db["global_players"] = global_players
            await save_global_db()
            await message.reply(f"✅ **لقب جدید (سراسری):** `{new_nickname}`")
            return

        # ===== دستورات مدیریت جهانی =====
        if lower_text == "global_help":
            sander = get_sander_id(user_id)
            is_gm = is_global_owner(sander) if sander else False
            status = "✅ بله" if is_gm else "❌ خیر"
            msg = f"""🌍 **راهنمای دستورات مالکیت جهانی**
━━━━━━━━━━━━━━━━━━━━━━━
👤 **وضعیت شما:** مالک جهانی ({status})
━━━━━━━━━━━━━━━━━━━━━━━
🛠️ **دستورات موجود:**

1️⃣ `global_set_owner [Sander ID]`
   - تعیین یک کاربر به عنوان مالک محلی در این چت.
   - فقط مالک جهانی می‌تواند استفاده کند.

2️⃣ `global_remove_owner`
   - حذف مالک محلی فعلی از این چت.
   - فقط مالک جهانی می‌تواند استفاده کند.

3️⃣ `global_status`
   - نمایش وضعیت مالکیت جهانی و مالک محلی این چت.

ℹ️ توجه: مالک جهانی در تمام چت‌ها قدرت مطلق دارد."""
            await message.reply(msg)
            await save_global_db()
            return

        if lower_text == "global_status":
            sander = get_sander_id(user_id)
            is_gm = is_global_owner(sander) if sander else False
            local_owner = chat_data.get("owner_sander_id")
            local_owner_display = "هیچ‌کس"
            if local_owner:
                for uid, p in chat_data["players"].items():
                    uid_sander = get_sander_id(uid)
                    if uid_sander and uid_sander.upper() == local_owner.upper():
                        local_owner_display = get_display_name_from_global(uid)
                        break
            status_text = "✅ فعال" if is_gm else "❌ غیرفعال"
            msg = f"""🌍 **وضعیت مالکیت جهانی**
━━━━━━━━━━━━━━━━━━━━━━━
👤 **کاربر فعلی:** `{sander if sander else 'ناشناس'}`
🔐 **وضعیت جهانی:** {status_text}
━━━━━━━━━━━━━━━━━━━━━━━
🏢 **مالک محلی این چت:**
   • شناسه: `{local_owner}`
   • نام: `{local_owner_display}`"""
            await message.reply(msg)
            await save_global_db()
            return

        if lower_text.startswith("global_set_owner"):
            sander = get_sander_id(user_id)
            if not sander or not is_global_owner(sander):
                await message.reply("⛔ **خطا:** شما دسترسی مالک جهانی ندارید.")
                await save_global_db()
                return
            parts = lower_text.split(maxsplit=1)
            if len(parts) < 2:
                await message.reply("⚠️ فرمت: `global_set_owner [Sander ID]`")
                await save_global_db()
                return
            target_sid_input = parts[1].strip().upper()
            target_uid = None
            global_players = global_db.get("global_players", {})
            for uid, gdata in global_players.items():
                if gdata.get("sander_id", "").upper() == target_sid_input:
                    target_uid = uid
                    break
            if not target_uid:
                await message.reply(f"❌ کاربری با `Sander ID` {target_sid_input} در این چت یافت نشد.")
                await save_global_db()
                return
            if target_uid == user_id:
                await message.reply("❌ نمی‌توانید خودتان را در همین چت به عنوان مالک محلی تعیین کنید (شما قبلاً مالک جهانی هستید).")
                await save_global_db()
                return
            old_owner = chat_data.get("owner_sander_id")
            chat_data["owner_sander_id"] = target_sid_input
            await save_global_db()
            new_owner_name = get_display_name_from_global(target_uid)
            old_owner_str = f"`{old_owner}`" if old_owner else "هیچ‌کس"
            await message.reply(f"""✅ **مالکیت محلی تغییر کرد!**
👤 **مالک جدید:** `{new_owner_name}` ({target_sid_input})
👋 **مالک قبلی:** {old_owner_str}""")
            return

        if lower_text == "global_remove_owner":
            sander = get_sander_id(user_id)
            if not sander or not is_global_owner(sander):
                await message.reply("⛔ **خطا:** شما دسترسی مالک جهانی ندارید.")
                await save_global_db()
                return
            chat_data["owner_sander_id"] = None
            await save_global_db()
            await message.reply("✅ **مالکیت محلی لغو شد.**")
            return

        # ===== سایر دستورات مالک =====
        if lower_text == "ریست دول":
            if not is_owner_flag:
                await message.reply("⛔ شما مالک نیستید!")
                await save_global_db()
                return
            count = 0
            for uid, p in chat_data["players"].items():
                if uid != user_id:
                    p["money"] = 0
                    count += 1
            await save_global_db()
            await message.reply(f"✅ **دول ریست شد!** (تعداد: {count})")
            return

        if lower_text.startswith("حذف"):
            if not is_owner_flag:
                await message.reply("⛔ شما مالک نیستید!")
                await save_global_db()
                return
            parts = lower_text.split()
            if len(parts) < 2:
                await message.reply("⚠️ فرمت: `حذف [کد]`")
                await save_global_db()
                return
            code_to_delete = parts[1].upper()
            deleted = False
            for key, fight in list(chat_data["fights"].items()):
                if fight["code"] == code_to_delete:
                    del chat_data["fights"][key]
                    deleted = True
                    break
            if deleted:
                await save_global_db()
                await message.reply(f"✅ مبارزه `{code_to_delete}` حذف شد.")
            else:
                await message.reply("❌ کد یافت نشد.")
                await save_global_db()
            return

        if lower_text.startswith("منفی"):
            if not is_owner_flag:
                await message.reply("⛔ شما مالک نیستید!")
                await save_global_db()
                return
            parts = lower_text.split()
            if len(parts) < 4:
                await message.reply("⚠️ فرمت: `منفی [مقدار] از [آیدی]`")
                await save_global_db()
                return
            try:
                amount_str = to_en_digits(parts[1])
                amount = int(amount_str)
                if amount <= 0:
                    raise ValueError
                target_sid_input = parts[3].upper().strip()
            except ValueError:
                await message.reply("⚠️ مقدار باید عدد مثبت باشد.")
                await save_global_db()
                return
            target_uid = None
            global_players = global_db.get("global_players", {})
            for uid, gdata in global_players.items():
                if gdata.get("sander_id", "").upper() == target_sid_input:
                    target_uid = uid
                    break
            if not target_uid:
                await message.reply(f"❌ کاربر `{target_sid_input}` یافت نشد.")
                await save_global_db()
                return
            if target_uid == user_id:
                await message.reply("❌ مالک نمی‌تواند پول خودش را کم کند!")
                await save_global_db()
                return
            target_player = chat_data["players"].get(target_uid)
            if not target_player:
                await message.reply("❌ کاربر در این چت ثبت نشده است!")
                await save_global_db()
                return
            current_money = safe_get_money(target_player)
            if current_money < amount:
                target_player["money"] = 0
                await save_global_db()
                await message.reply(f"✅ موجودی به صفر رسید.")
            else:
                target_player["money"] -= amount
                await save_global_db()
                await message.reply(f"""✅ **عملیات موفق!**
کاربر: `{target_sid_input}`
موجودی بعد: {target_player['money']}""")
            return

        if lower_text.startswith("ساخت کد هدیه"):
            if not is_owner_flag:
                await message.reply("⛔ شما مالک نیستید!")
                await save_global_db()
                return
            parts = lower_text.split()
            if len(parts) < 6:
                await message.reply("⚠️ فرمت: `ساخت کد هدیه [مبلغ] بین [تعداد] اسم [نام]`")
                await save_global_db()
                return
            try:
                idx_coin = -1
                for i, word in enumerate(parts):
                    if word == "هدیه":
                        idx_coin = i + 1
                        break
                if idx_coin == -1 or idx_coin >= len(parts):
                    raise ValueError
                coin_str = to_en_digits(parts[idx_coin])
                coin_amount = int(coin_str)
                idx_max = -1
                for i in range(idx_coin + 1, len(parts)):
                    if parts[i] == "بین":
                        idx_max = i + 1
                        break
                if idx_max == -1 or idx_max >= len(parts):
                    raise ValueError
                max_str = to_en_digits(parts[idx_max])
                max_users = int(max_str)
                idx_name_start = -1
                for i in range(idx_max + 1, len(parts)):
                    if parts[i] == "اسم":
                        idx_name_start = i + 1
                        break
                if idx_name_start == -1:
                    idx_name_start = idx_max + 1
                gift_name = " ".join(parts[idx_name_start:])
                if coin_amount <= 0 or max_users <= 0:
                    raise ValueError
            except ValueError:
                await message.reply("⚠️ مقادیر عددی باید مثبت باشند.")
                await save_global_db()
                return
            code_to_use = "".join(gift_name.split()).upper()
            existing = any(g["code"] == code_to_use for g in chat_data.get("gift_codes", []))
            if existing:
                await message.reply(f"❌ کد `{code_to_use}` تکراری است!")
                await save_global_db()
                return
            new_gift = {
                "code": code_to_use,
                "display_name": gift_name,
                "amount": coin_amount,
                "max_users": max_users,
                "used_count": 0,
                "created_at": time.time()
            }
            if "gift_codes" not in chat_data:
                chat_data["gift_codes"] = []
            chat_data["gift_codes"].append(new_gift)
            await save_global_db()
            await message.reply(f"""✅ **کد هدیه ساخته شد!**
🔑 کد: `{code_to_use}`
💰 مبلغ: {coin_amount}
👥 محدودیت: {max_users}""")
            return

        if lower_text.startswith("هدیه حذف"):
            if not is_owner_flag:
                await message.reply("⛔ شما مالک نیستید!")
                await save_global_db()
                return
            parts = lower_text.split()
            if len(parts) < 2:
                await message.reply("⚠️ فرمت: `هدیه حذف [کد]`")
                await save_global_db()
                return
            code_to_delete = parts[1].upper()
            gifts_list = chat_data.get("gift_codes", [])
            found_idx = None
            for i, g in enumerate(gifts_list):
                if g["code"] == code_to_delete:
                    found_idx = i
                    break
            if found_idx is not None:
                del gifts_list[found_idx]
                await save_global_db()
                await message.reply(f"✅ کد `{code_to_delete}` حذف شد.")
            else:
                await message.reply("❌ کد یافت نشد.")
                await save_global_db()
            return

        if lower_text == "لیست هدیه":
            if not is_owner_flag:
                await message.reply("⛔ شما مالک نیستید!")
                await save_global_db()
                return
            gifts = chat_data.get("gift_codes", [])
            if not gifts:
                await message.reply("هیچ کد هدیه‌ای ساخته نشده است.")
                await save_global_db()
                return
            lines = []
            for g in gifts:
                status = f"{g['used_count']}/{g['max_users']}"
                lines.append(f"کد: `{g['code']}` | مبلغ: {g['amount']} | وضعیت: {status}")
            await message.reply("\n".join(lines))
            await save_global_db()
            return

        # ===== جوایز رایگان =====
        if lower_text == "سانتی":
            now = time.time()
            global_time = chat_data.get("global_sanati_time", 0)
            cooldown_24h = 24 * 60 * 60
            if now - global_time < cooldown_24h:
                remaining = cooldown_24h - (now - global_time)
                await message.reply(f"✅ جایزه امروز داده شد. زمان بعدی: {format_time(remaining)}")
                await save_global_db()
                return
            prize_amount = 5
            before_money = safe_get_money(player)
            after_money = before_money + prize_amount
            player["money"] = after_money
            chat_data["global_sanati_time"] = now
            await save_global_db()
            await message.reply(f"""🎉 **جایزه روزانه سانتی!**
🏆 برنده: {get_display_name_from_global(user_id)}
💰 مقدار: {prize_amount}
قبل: {before_money} | بعد: {after_money}""")
            return

        if lower_text == "دود":
            now = time.time()
            last_time = player.get("last_dood_time", 0)
            cooldown_3h = 3 * 60 * 60
            if now - last_time < cooldown_3h:
                remaining = cooldown_3h - (now - last_time)
                await message.reply(f"⏳ زمان باقی‌مانده: {format_time(remaining)}")
                await save_global_db()
                return
            amount = random.randint(1, 30)
            before_money = safe_get_money(player)
            after_money = before_money + amount
            player["money"] = after_money
            player["last_dood_time"] = now
            await save_global_db()
            await message.reply(f"""🎁 **دود ۳ ساعته!**
مقدار: {amount}
قبل: {before_money} | بعد: {after_money}""")
            return

        # گردونه با شانس پوچ کمتر
        if lower_text == "گردونه":
            now = time.time()
            last_spin = player.get("last_spin_time", 0)
            if now - last_spin < SPIN_COOLDOWN:
                remaining = SPIN_COOLDOWN - (now - last_spin)
                await message.reply(f"⏳ زمان باقی‌مانده: {format_time(remaining)}")
                await save_global_db()
                return
            weights = [("پوچ", 15), ("پوچ", 10), (5, 15), (10, 12), (13, 10), (20, 8), (50, 5), (100, 3), (500, 2)]
            total_weight = sum(w for _, w in weights)
            rand_val = random.uniform(0, total_weight)
            current = 0
            result = None
            for item, weight in weights:
                current += weight
                if rand_val <= current:
                    result = item
                    break
            if isinstance(result, int):
                before_money = safe_get_money(player)
                after_money = before_money + result
                player["money"] = after_money
                player["last_spin_time"] = now
                await save_global_db()
                await message.reply(f"""🎡 **نتیجه گردونه!**
🎁 جایزه: {result} سانت
قبل: {before_money} | بعد: {after_money}""")
            else:
                player["last_spin_time"] = now
                await save_global_db()
                await message.reply("😢 **پوچ!** دوباره تلاش کنید.")
            return

        # ===== انتقال پول =====
        if lower_text.startswith("اهدای سانت"):
            parts = lower_text[len("اهدای سانت"):].strip().split()
            if len(parts) < 2:
                await message.reply("⚠️ فرمت: `اهدای سانت [مقدار] [آیدی]`")
                await save_global_db()
                return
            try:
                amount_str = to_en_digits(parts[0].replace("سانت", ""))
                amount = int(amount_str)
                if amount <= 0:
                    raise ValueError
            except:
                await message.reply("⚠️ مبلغ باید عدد مثبت باشد.")
                await save_global_db()
                return
            target_sid = parts[1].upper()
            target_uid = None
            global_players = global_db.get("global_players", {})
            for uid, gdata in global_players.items():
                if gdata.get("sander_id", "").upper() == target_sid:
                    target_uid = uid
                    break
            if not target_uid:
                await message.reply(f"❌ کاربر `{target_sid}` یافت نشد.")
                await save_global_db()
                return
            if target_uid == user_id:
                await message.reply("❌ نمی‌توانید به خودتان بدهید!")
                await save_global_db()
                return
            target_player = chat_data["players"].get(target_uid)
            if not target_player:
                await message.reply("❌ کاربر در این چت ثبت نشده است!")
                await save_global_db()
                return
            now = time.time()
            last_time = player.get("last_transfer_time", 0)
            if now - last_time < 60:
                await message.reply(f"⏳ زمان باقی‌مانده: {format_time(60 - (now - last_time))}")
                await save_global_db()
                return
            is_sender_owner = is_owner(chat_data, user_id)
            sender_money = safe_get_money(player)
            if not is_sender_owner and sender_money < amount:
                await message.reply(f"❌ موجودی کافی ندارید! نیاز به {amount}.")
                await save_global_db()
                return
            if not is_sender_owner:
                player["money"] -= amount
            target_player["money"] += amount
            player["last_transfer_time"] = now
            player["stats"]["transfer_count"] += 1
            await save_global_db()
            sender_display = format_money(player["money"], is_sender_owner)
            receiver_display = format_money(safe_get_money(target_player), is_owner(chat_data, target_uid))
            await message.reply(f"""✅ **انتقال موفق!**
به: `{get_display_name_from_global(target_uid)}` ({target_sid})
مقدار: {amount}
شما: {sender_display}
گیرنده: {receiver_display}""")
            return

        # ===== هدیه =====
        if lower_text.startswith("هدیه"):
            parts = lower_text.split()
            if len(parts) < 2:
                await message.reply("⚠️ فرمت: `هدیه [کد]`")
                await save_global_db()
                return
            code_input = "".join(parts[1].split()).upper()
            found_gift = None
            for g in chat_data.get("gift_codes", []):
                if g["code"] == code_input:
                    found_gift = g
                    break
            if not found_gift and code_input == GIFT_CODE_DEFAULT:
                current_count = chat_data.get("default_gift_count", 0)
                if current_count >= MAX_GIFT_USERS_DEFAULT:
                    await message.reply(f"❌ سقف کاربران پر شده است!")
                    await save_global_db()
                    return
                found_gift = {
                    "code": GIFT_CODE_DEFAULT,
                    "amount": GIFT_AMOUNT_DEFAULT,
                    "max_users": MAX_GIFT_USERS_DEFAULT,
                    "used_count": current_count
                }
            if not found_gift:
                await message.reply(f"❌ کد هدیه `{code_input}` نامعتبر است.")
                await save_global_db()
                return
            if code_input in player["used_gift_codes"]:
                await message.reply("❌ قبلاً از این کد استفاده کرده‌اید!")
                await save_global_db()
                return
            if found_gift["used_count"] >= found_gift["max_users"]:
                await message.reply("❌ تعداد استفاده تکمیل شده است!")
                await save_global_db()
                return
            before_money = safe_get_money(player)
            player["money"] += found_gift["amount"]
            player["used_gift_codes"].append(code_input)
            if found_gift["code"] != GIFT_CODE_DEFAULT:
                for g in chat_data["gift_codes"]:
                    if g["code"] == code_input:
                        g["used_count"] += 1
                        break
            else:
                current_count = chat_data.get("default_gift_count", 0)
                chat_data["default_gift_count"] = current_count + 1
            await save_global_db()
            await message.reply(f"""🎁 **کد معتبر!**
مبلغ: {found_gift['amount']}
قبل: {before_money} | بعد: {player['money']}""")
            return

        # ===== دولداران =====
        if lower_text.startswith("دولداران"):
            parts = lower_text.split()
            if len(parts) == 1:
                sorted_players = sorted(chat_data["players"].items(), key=lambda x: safe_get_money(x[1]), reverse=True)
                top_list = []
                is_current_owner = is_owner(chat_data, user_id)
                for uid, p in sorted_players:
                    if is_current_owner and uid == user_id:
                        continue
                    display = get_display_name_from_global(uid)
                    money_str = format_money(safe_get_money(p))
                    top_list.append(f"#{len(top_list)+1}. `{display}` → {money_str}")
                if not top_list:
                    await message.reply("هیچ کاربری غیر از مالک ثبت نشده است!")
                    await save_global_db()
                    return
                await message.reply(f"""🏆 **لیست کامل ثروتمندان (همه)**
━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(top_list)}
━━━━━━━━━━━━━━━━━━━━━━━
*کل کاربران فعال:* {len(top_list)}""")
                await save_global_db()
                return
            try:
                limit_str = to_en_digits(parts[1])
                limit = int(limit_str)
                if limit < 1:
                    raise ValueError
            except ValueError:
                await message.reply("⚠️ لطفاً یک عدد معتبر و مثبت وارد کنید.")
                await save_global_db()
                return
            all_users = [uid for uid in chat_data["players"].keys()]
            total_available = len(all_users)
            if limit > total_available:
                await message.reply(f"""⚠️ **توجه!**
تعداد درخواستی: `{limit}` نفر
کل کاربران موجود: `{total_available}` نفر است.""")
                await save_global_db()
                return
            sorted_players = sorted(chat_data["players"].items(), key=lambda x: safe_get_money(x[1]), reverse=True)
            top_list = []
            is_current_owner = is_owner(chat_data, user_id)
            count = 0
            for uid, p in sorted_players:
                if count >= limit:
                    break
                if is_current_owner and uid == user_id:
                    continue
                display = get_display_name_from_global(uid)
                money_str = format_money(safe_get_money(p))
                top_list.append(f"{count+1}. `{display}` → {money_str}")
                count += 1
            if not top_list:
                await message.reply("هیچ کاربری یافت نشد!")
                await save_global_db()
                return
            await message.reply(f"""🏆 **لیست {limit} نفر اول ثروتمندان**
━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(top_list)}
━━━━━━━━━━━━━━━━━━━━━━━
*نمایش {len(top_list)} نفر از {total_available} کاربر.*""")
            await save_global_db()
            return

        # ===== پروفایل =====
        if lower_text == "پروف":
            stats = player.get("stats", {})
            wins = stats.get('wins', 0)
            losses = stats.get('losses', 0)
            total_fights = stats.get('total_fights', 0)
            win_rate = (wins / total_fights * 100) if total_fights > 0 else 0.0
            money_str = format_money(safe_get_money(player), is_owner_flag)
            nickname = global_db.get("global_players", {}).get(user_id, {}).get("nickname") or 'بدون لقب'
            sander_id = get_sander_id(user_id) or "نامشخص"
            msg = f"""
👤 **پروفایل شخصی شما**
━━━━━━━━━━━━━━━━━━━━━━━
🆔 **Sander ID:** `{sander_id}`
💎 **لقب:** `{nickname}`
💰 **موجودی:** {money_str}
━━━━━━━━━━━━━━━━━━━━━━━
⚔️ **آمار مبارزات:**
   • کل بازی‌ها: {total_fights}
   • برنده‌ها: {wins}
   • بازنده‌ها: {losses}
   • ضریب برد: {win_rate:.2f}%
━━━━━━━━━━━━━━━━━━━━━━━
🎁 **تراکنش‌ها:**
   • تعداد انتقال‌ها: {stats.get('transfer_count', 0)}"""
            await message.reply(msg)
            await save_global_db()
            return

        # ===== مبارزه =====
        if lower_text.startswith("مبارزه"):
            parts = lower_text.split()
            if len(parts) < 2:
                await message.reply("⚠️ فرمت: `مبارزه [مبلغ]`")
                await save_global_db()
                return
            try:
                bet_str = to_en_digits(parts[1].replace("سانت", ""))
                bet = int(bet_str)
                if bet <= 0:
                    raise ValueError
            except ValueError:
                await message.reply("⚠️ مبلغ باید یک عدد مثبت باشد.")
                await save_global_db()
                return
            is_requester_owner = is_owner(chat_data, user_id)
            sender_money = safe_get_money(player)
            if not is_requester_owner and sender_money < bet:
                await message.reply(f"❌ موجودی کافی نیست! نیاز به {bet} سانت دارید.")
                await save_global_db()
                return
            keys_to_del = [k for k, f in chat_data["fights"].items() 
                           if (f["requester"] == user_id or f["target"] == user_id) 
                           and f["status"] in ["pending", "waiting_for_acceptance"]]
            for k in keys_to_del:
                del chat_data["fights"][k]
            code = generate_fight_code()
            key = f"{user_id}_{int(time.time())}"
            chat_data["fights"][key] = {
                "code": code, 
                "requester": user_id, 
                "target": None,
                "status": "waiting_for_acceptance", 
                "created_at": time.time(), 
                "bet_amount": bet,
                "is_requester_owner": is_requester_owner
            }
            await save_global_db()
            await message.reply(f"""🔥 **دعوت مبارزه ارسال شد!**
━━━━━━━━━━━━━━━━━━━━━━━
💰 **شرط:** {bet} سانت
🔑 **کد مبارزه:** `{code}`
💰 **موجودی شما:** {format_money(safe_get_money(player), is_owner_flag)}
━━━━━━━━━━━━━━━━━━━━━━━
هر کسی کد بالا را با دستور `تایید` وارد کند، حریف شما می‌شود.""")
            return

        # ===== لیست مبارزه =====
        if lower_text == "لیست مبارزه":
            fights = []
            active_statuses = ["pending", "waiting_for_acceptance"]
            for k, f in chat_data["fights"].items():
                if f["status"] in active_statuses:
                    req_name = get_display_name_from_global(f["requester"])
                    tgt_name = get_display_name_from_global(f["target"]) if f["target"] else "منتظر..."
                    fights.append(f"کد: `{f['code']}` | {req_name} ⚔️ {tgt_name}")
            if not fights:
                await message.reply("هیچ مبارزه فعالی وجود ندارد.")
            else:
                await message.reply("\n".join(fights))
            await save_global_db()
            return

        # ===== تایید مبارزه =====
        if lower_text.startswith("تایید"):
            parts = lower_text.split()
            if len(parts) < 2:
                await message.reply("⚠️ فرمت: `تایید [کد]`")
                await save_global_db()
                return
            code = parts[1].upper()
            found_match = False
            for k, f in list(chat_data["fights"].items()):
                if f["code"] == code and f["status"] in ["pending", "waiting_for_acceptance"]:
                    found_match = True
                    requester_uid = f["requester"]
                    target_uid = f["target"]
                    if user_id == requester_uid:
                        await message.reply("❌ شما نمی‌توانید دعوت خودتان را تایید کنید!")
                        await save_global_db()
                        continue
                    if target_uid is None:
                        is_target_owner = is_owner(chat_data, user_id)
                        target_money = safe_get_money(player)
                        if not is_target_owner and target_money < f["bet_amount"]:
                            await message.reply(f"❌ موجودی شما کافی نیست! نیاز به {f['bet_amount']} سانت دارید.")
                            await save_global_db()
                            continue
                        if not is_target_owner:
                            player["money"] -= f["bet_amount"]
                        f["target"] = user_id
                        f["status"] = "pending"
                        winner_uid = f["requester"] if random.random() > 0.5 else f["target"]
                        loser_uid = f["target"] if winner_uid == f["requester"] else f["requester"]
                        bet_val = f["bet_amount"]
                        if "stats" not in chat_data["players"][winner_uid]:
                            chat_data["players"][winner_uid]["stats"] = {"total_fights": 0, "wins": 0, "losses": 0, "transfer_count": 0}
                        if "stats" not in chat_data["players"][loser_uid]:
                            chat_data["players"][loser_uid]["stats"] = {"total_fights": 0, "wins": 0, "losses": 0, "transfer_count": 0}
                        chat_data["players"][winner_uid]["stats"]["wins"] += 1
                        chat_data["players"][loser_uid]["stats"]["losses"] += 1
                        chat_data["players"][winner_uid]["stats"]["total_fights"] += 1
                        chat_data["players"][loser_uid]["stats"]["total_fights"] += 1
                        if not is_owner(chat_data, winner_uid):
                            winner_player = chat_data["players"][winner_uid]
                            winner_player["money"] += bet_val
                        if not is_owner(chat_data, loser_uid):
                            loser_player = chat_data["players"][loser_uid]
                            loser_money = safe_get_money(loser_player)
                            if loser_money >= bet_val:
                                loser_player["money"] -= bet_val
                            else:
                                loser_player["money"] = 0
                        del chat_data["fights"][k]
                        await save_global_db()
                        w_name = get_display_name_from_global(winner_uid)
                        l_name = get_display_name_from_global(loser_uid)
                        w_money_str = format_money(safe_get_money(chat_data["players"][winner_uid]), is_owner(chat_data, winner_uid))
                        l_money_str = format_money(safe_get_money(chat_data["players"][loser_uid]), is_owner(chat_data, loser_uid))
                        await message.reply(f"""✅ **نتیجه مبارزه اعلام شد!**
━━━━━━━━━━━━━━━━━━━━━━━
🏆 **برنده:** `{w_name}`
😔 **بازنده:** `{l_name}`
💰 **جایزه:** {bet_val} سانت
━━━━━━━━━━━━━━━━━━━━━━━
💵 **موجودی نهایی:**
   • برنده: {w_money_str}
   • بازنده: {l_money_str}""")
                        break
                    else:
                        await message.reply("❌ این مبارزه قبلاً توسط شخص دیگری تایید شده است!")
                        await save_global_db()
                        continue
            if not found_match:
                await message.reply("❌ کد وارد شده اشتباه است یا مبارزه تمام/لغو شده است.")
            await save_global_db()
            return

        # ===== لغو مبارزه =====
        if lower_text == "غیرفعال":
            cancelled = False
            for k, f in list(chat_data["fights"].items()):
                if (f["requester"] == user_id or f["target"] == user_id) and f["status"] in ["pending", "waiting_for_acceptance"]:
                    f["status"] = "cancelled"
                    await save_global_db()
                    cancelled = True
                    break
            if cancelled:
                await message.reply("✅ مبارزه لغو شد.")
            else:
                await message.reply("⚠️ شما هیچ مبارزه فعالی برای لغو ندارید.")
            return

        # ===== متن (آمار پیام‌ها) =====
        if lower_text == "متن":
            if not is_owner_flag:
                await message.reply("⛔ **خطا:** شما دسترسی مشاهده آمار پیام‌ها را ندارید.")
                await save_global_db()
                return
            logs = chat_data.get("chat_logs", [])
            counts = chat_data.get("user_message_counts", {})
            if not logs:
                await message.reply("📝 هنوز هیچ پیامی در این چت ثبت نشده است.")
                await save_global_db()
                return
            msg_lines = []
            msg_lines.append("📜 **لیست پیام‌های چت (فقط برای مدیر):**")
            msg_lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
            recent_logs = logs[-30:] 
            for idx, log in enumerate(recent_logs):
                msg_lines.append(f"{idx+1}. {log}")
            if len(logs) > 30:
                msg_lines.append(f"... و {len(logs) - 30} پیام دیگر در دیتابیس ذخیره شده است.")
            msg_lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
            msg_lines.append("📊 **آمار تعداد پیام هر کاربر:**")
            sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            rank = 1
            for uid, count in sorted_counts:
                p_name = get_display_name_from_global(uid)
                msg_lines.append(f"{rank}. {p_name}: {count} پیام")
                rank += 1
            full_msg = "\n".join(msg_lines)
            await send_long_message(message, full_msg)
            await save_global_db()
            return

        # ===== کازینو =====
        if lower_text == "کازینو":
            if chat_id in casino_games:
                await message.reply("⚠️ در حال حاضر یک بازی کازینو در این چت در جریان است. لطفاً کمی صبر کنید.")
                await save_global_db()
                return

            last_casino = player.get("last_casino_time", 0)
            now = time.time()
            if now - last_casino < CASINO_COOLDOWN:
                remaining = CASINO_COOLDOWN - (now - last_casino)
                await message.reply(f"⏳ لطفاً {format_time(remaining)} صبر کنید تا دوباره کازینو بازی کنید.")
                await save_global_db()
                return

            player["last_casino_time"] = now
            await save_global_db()

            casino_games[chat_id] = {
                "host": user_id,
                "stage": "waiting_bet",
                "bet": None,
                "player_count": None,
                "players": [],
                "code": None,
                "created_at": time.time()
            }
            await message.reply("🎰 **بازی کازینو شروع شد!**\nلطفاً مبلغ شرط خود را به **سانت** وارد کنید (عدد مثبت).\n⏳ اگر عددی وارد نکنید، بازی کنسل می‌شود.")
            asyncio.create_task(auto_cancel_casino(chat_id, message))
            return

        # مرحله waiting_bet
        if chat_id in casino_games and casino_games[chat_id]["stage"] == "waiting_bet":
            if user_id != casino_games[chat_id]["host"]:
                return
            try:
                bet_amount = int(to_en_digits(text))
                if bet_amount <= 0:
                    raise ValueError
            except:
                await message.reply("❌ عدد نامعتبر! بازی لغو شد.")
                del casino_games[chat_id]
                await save_global_db()
                return

            if not is_owner_flag and safe_get_money(player) < bet_amount:
                await message.reply(f"❌ موجودی شما کافی نیست! نیاز به {bet_amount} سانت دارید.")
                del casino_games[chat_id]
                await save_global_db()
                return

            casino_games[chat_id]["bet"] = bet_amount
            casino_games[chat_id]["stage"] = "waiting_players"
            await message.reply(f"✅ مبلغ شرط: {bet_amount} سانت\n\nحالا تعداد بازیکنان را وارد کنید (۱، ۲ یا ۳):")
            await save_global_db()
            return

        # مرحله waiting_players
        if chat_id in casino_games and casino_games[chat_id]["stage"] == "waiting_players":
            if user_id != casino_games[chat_id]["host"]:
                return
            try:
                count = int(to_en_digits(text))
                if count not in [1, 2, 3]:
                    raise ValueError
            except:
                await message.reply("❌ عدد نامعتبر! بازی لغو شد.")
                del casino_games[chat_id]
                await save_global_db()
                return

            casino_games[chat_id]["player_count"] = count
            casino_games[chat_id]["stage"] = "waiting_join"
            casino_games[chat_id]["players"] = [user_id]

            if count == 1:
                casino_games[chat_id]["stage"] = "playing"
                await process_single_player_game(chat_id, message)
                return
            else:
                code = generate_casino_code()
                casino_games[chat_id]["code"] = code
                await message.reply(f"🎲 **بازی با {count} نفر ایجاد شد!**\n\n🔑 کد ورود: `{code}`\n\nسایر بازیکنان با دستور `ورود {code}` می‌توانند وارد بازی شوند.\nپس از تکمیل تعداد، بازی شروع می‌شود.")
                asyncio.create_task(check_casino_ready(chat_id, message))
                await save_global_db()
                return

        # ورود به بازی کازینو
        if lower_text.startswith("ورود"):
            parts = lower_text.split()
            if len(parts) < 2:
                await message.reply("⚠️ فرمت: `ورود [کد]`")
                await save_global_db()
                return
            code = parts[1]
            if chat_id not in casino_games:
                await message.reply("❌ هیچ بازی کازینو فعالی در این چت وجود ندارد.")
                await save_global_db()
                return
            game = casino_games[chat_id]
            if game["stage"] != "waiting_join":
                await message.reply("❌ این بازی در مرحله ورود نیست.")
                await save_global_db()
                return
            if game["code"] != code:
                await message.reply("❌ کد وارد شده اشتباه است.")
                await save_global_db()
                return
            if user_id in game["players"]:
                await message.reply("⚠️ شما قبلاً وارد بازی شده‌اید.")
                await save_global_db()
                return
            if len(game["players"]) >= game["player_count"]:
                await message.reply("❌ تعداد بازیکنان تکمیل شده است.")
                await save_global_db()
                return

            last_casino = player.get("last_casino_time", 0)
            now = time.time()
            if now - last_casino < CASINO_COOLDOWN:
                remaining = CASINO_COOLDOWN - (now - last_casino)
                await message.reply(f"⏳ شما باید {format_time(remaining)} صبر کنید تا بتوانید وارد بازی شوید.")
                await save_global_db()
                return

            player_data = chat_data["players"].get(user_id)
            if not is_owner(chat_data, user_id) and safe_get_money(player_data) < game["bet"]:
                await message.reply(f"❌ موجودی شما کافی نیست! نیاز به {game['bet']} سانت دارید.")
                await save_global_db()
                return

            player["last_casino_time"] = now
            game["players"].append(user_id)
            await save_global_db()
            await message.reply(f"✅ شما با موفقیت وارد بازی شدید! ({len(game['players'])}/{game['player_count']})")

            if len(game["players"]) == game["player_count"]:
                game["stage"] = "playing"
                await message.reply("🎯 تعداد بازیکنان تکمیل شد! بازی در حال شروع...")
                await asyncio.sleep(2)
                await process_multiplayer_game(chat_id, message)
            return

    except Exception as e:
        print(f"Error in handle_message: {e}")
        traceback.print_exc()
        await message.reply(f"❌ خطایی رخ داد: {str(e)[:50]}")
        await save_global_db()

# ============================
#  راه‌اندازی Flask در ترد جداگانه
# ============================

def start_web_panel():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ============================
#  اجرای اصلی
# ============================

async def main():
    print("🚀 ربات هوشمند سانتی در حال راه‌اندازی...")
    load_global_db()
    print(f"✅ دیتابیس از {DATA_FILE} بارگذاری شد.")
    print(f"✅ مالک جهانی: {GLOBAL_OWNER_SANDER_ID}")

    web_thread = threading.Thread(target=start_web_panel, daemon=True)
    web_thread.start()
    print("✅ پنل مدیریت کامل در http://0.0.0.0:5000 راه‌اندازی شد.")

    try:
        await bot.run()
    except KeyboardInterrupt:
        print("ربات خاموش شد.")
        await save_global_db()
    except Exception as e:
        print(f"خطای جدی: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
