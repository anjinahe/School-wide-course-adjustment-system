// 获取班级ID（从URL路径中提取）
const classId = window.location.pathname.split('/')[2];

// 更新时间显示
function updateLastUpdateTime() {
    const now = new Date();
    const timeString = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('lastUpdate').textContent = timeString;
}

// 格式化课程数据并显示
function renderSchedule(courses) {
    const scheduleBody = document.getElementById('scheduleBody');
    if (!courses || courses.length === 0) {
        scheduleBody.innerHTML = '<tr><td colspan="4" class="no-data">暂无课程数据</td></tr>';
        return;
    }
    
    // 按时间段排序
    const timeSlotOrder = ['上午1', '上午2', '下午1', '下午2'];
    courses.sort((a, b) => timeSlotOrder.indexOf(a.time_slot) - timeSlotOrder.indexOf(b.time_slot));
    
    // 生成表格内容
    scheduleBody.innerHTML = courses.map(course => `
        <tr>
            <td>${course.time_slot}</td>
            <td>${course.subject}</td>
            <td>${course.current_teacher}</td>
            <td>${course.adjustment ? '<span class="adjusted">已调课</span>' : '正常'}</td>
        </tr>
    `).join('');
}

// 显示调课通知
function renderAdjustmentNotices(courses) {
    const noticesContainer = document.getElementById('adjustmentNotices');
    const adjustedCourses = courses.filter(course => course.adjustment);
    
    if (adjustedCourses.length === 0) {
        noticesContainer.innerHTML = '';
        return;
    }
    
    noticesContainer.innerHTML = adjustedCourses.map(course => `
        <div class="adjustment-notice">
            <div class="notice-title">${course.time_slot} ${course.subject} 调课通知</div>
            <div class="notice-content">原教师: ${course.original_teacher} → 新教师: ${course.current_teacher}</div>
        </div>
    `).join('');
}

// 获取班级课程数据
async function fetchClassCourses() {
    try {
        const response = await fetch(`/api/class/${classId}/courses`);
        if (!response.ok) {
            throw new Error('网络响应不正常');
        }
        const courses = await response.json();
        renderSchedule(courses);
        renderAdjustmentNotices(courses);
        updateLastUpdateTime();
    } catch (error) {
        console.error('获取课程数据失败:', error);
        const scheduleBody = document.getElementById('scheduleBody');
        scheduleBody.innerHTML = '<tr><td colspan="4" class="error">获取课程数据失败，请刷新页面重试</td></tr>';
    }
}

// 初始加载课程数据
fetchClassCourses();

// 设置定时刷新（每30秒）
setInterval(fetchClassCourses, 30000);