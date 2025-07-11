// 调课申请模态框控制
let currentCourseId = null;
const adjustModal = document.getElementById('adjustModal');

function openAdjustModal(courseId) {
    currentCourseId = courseId;
    document.getElementById('courseId').value = courseId;
    adjustModal.style.display = 'block';
}

function closeAdjustModal() {
    adjustModal.style.display = 'none';
    document.getElementById('adjustForm').reset();
}

// 关闭模态框当点击外部区域
window.onclick = function(event) {
    if (event.target == adjustModal) {
        closeAdjustModal();
    }
}

// 选项卡切换
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // 移除所有活动状态
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.style.display = 'none');
        
        // 设置当前活动状态
        btn.classList.add('active');
        const tabId = btn.getAttribute('data-tab');
        document.getElementById(`${tabId}-content`).style.display = 'block';
        
        // 加载对应内容
        if (tabId === 'received') {
            loadReceivedRequests();
        } else {
            loadSentRequests();
        }
    });
});

// 提交调课申请
document.getElementById('adjustForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const targetTeacher = document.getElementById('targetTeacher').value;
    const reason = document.getElementById('reason').value;
    
    try {
        const response = await fetch('/api/adjustment/request', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                course_id: currentCourseId,
                target_teacher_id: targetTeacher,
                reason: reason
            })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            alert('调课申请已提交！');
            closeAdjustModal();
            loadSentRequests(); // 更新已发送申请列表
        } else {
            alert(`错误: ${result.message}`);
        }
    } catch (error) {
        console.error('提交申请失败:', error);
        alert('提交申请失败，请重试');
    }
});

// 加载收到的调课申请
async function loadReceivedRequests() {
    try {
        const response = await fetch('/api/teacher/adjustments');
        const result = await response.json();
        
        const container = document.getElementById('received-content');
        if (result.received && result.received.length > 0) {
            container.innerHTML = `
                <table class="request-table">
                    <thead>
                        <tr>
                            <th>课程</th>
                            <th>申请人</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${result.received.map(req => `
                            <tr>
                                <td>${req.course_id}</td>
                                <td>${req.from_teacher}</td>
                                <td>${getStatusText(req.status)}</td>
                                <td>${getActionButtons(req)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            // 添加按钮事件监听
            attachActionButtonListeners();
        } else {
            container.innerHTML = '<p class="no-data">暂无收到的调课申请</p>';
        }
    } catch (error) {
        console.error('加载收到的申请失败:', error);
        document.getElementById('received-content').innerHTML = '<p class="error">加载失败，请刷新页面重试</p>';
    }
}

// 加载已发送的调课申请
async function loadSentRequests() {
    try {
        const response = await fetch('/api/teacher/adjustments');
        const result = await response.json();
        
        const container = document.getElementById('sent-content');
        if (result.sent && result.sent.length > 0) {
            container.innerHTML = `
                <table class="request-table">
                    <thead>
                        <tr>
                            <th>课程</th>
                            <th>目标教师</th>
                            <th>状态</th>
                            <th>提交时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${result.sent.map(req => `
                            <tr>
                                <td>${req.course_id}</td>
                                <td>${req.to_teacher}</td>
                                <td>${getStatusText(req.status)}</td>
                                <td>${formatTime(req.created_at)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            container.innerHTML = '<p class="no-data">暂无已发送的调课申请</p>';
        }
    } catch (error) {
        console.error('加载已发送的申请失败:', error);
        document.getElementById('sent-content').innerHTML = '<p class="error">加载失败，请刷新页面重试</p>';
    }
}

// 辅助函数：获取状态文本
function getStatusText(status) {
    switch(status) {
        case 'pending': return '<span class="status-pending">待处理</span>';
        case 'approved': return '<span class="status-approved">已批准</span>';
        case 'rejected': return '<span class="status-rejected">已拒绝</span>';
        default: return status;
    }
}

// 辅助函数：获取操作按钮
function getActionButtons(request) {
    if (request.status !== 'pending') {
        return '-';
    }
    return `
        <button class="btn-approve" data-id="${request.id}">批准</button>
        <button class="btn-reject" data-id="${request.id}">拒绝</button>
    `;
}

// 辅助函数：格式化时间
function formatTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

// 为操作按钮添加事件监听
function attachActionButtonListeners() {
    document.querySelectorAll('.btn-approve').forEach(btn => {
        btn.addEventListener('click', async function() {
            const requestId = this.getAttribute('data-id');
            await handleAdjustmentAction(requestId, 'approve');
        });
    });
    
    document.querySelectorAll('.btn-reject').forEach(btn => {
        btn.addEventListener('click', async function() {
            const requestId = this.getAttribute('data-id');
            await handleAdjustmentAction(requestId, 'reject');
        });
    });
}

// 处理调课申请操作
async function handleAdjustmentAction(requestId, action) {
    try {
        const response = await fetch(`/api/adjustment/${requestId}/handle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action: action })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            alert(result.message);
            loadReceivedRequests(); // 刷新收到的申请列表
        } else {
            alert(`错误: ${result.message}`);
        }
    } catch (error) {
        console.error('处理申请失败:', error);
        alert('处理申请失败，请重试');
    }
}

// 页面加载时初始化
window.addEventListener('DOMContentLoaded', function() {
    // 默认加载收到的申请
    loadReceivedRequests();
});