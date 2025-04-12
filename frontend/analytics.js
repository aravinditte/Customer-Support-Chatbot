// Initialize charts and data
let categoriesChart = null;
let satisfactionChart = null;

// Load analytics data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadAnalyticsData();
    
    // Set up refresh button
    document.getElementById('refreshButton').addEventListener('click', loadAnalyticsData);
    
    // Set up navigation link handlers
    setupNavigationLinks();
});

// Handle navigation links
function setupNavigationLinks() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Create and show modal
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.style.display = 'flex';
            
            const modalContent = document.createElement('div');
            modalContent.className = 'modal-content';
            
            const message = document.createElement('p');
            message.textContent = 'This feature is not available in the demo version.';
            
            const closeButton = document.createElement('button');
            closeButton.className = 'modal-close';
            closeButton.textContent = 'Close';
            closeButton.addEventListener('click', function() {
                document.body.removeChild(modal);
            });
            
            modalContent.appendChild(message);
            modalContent.appendChild(closeButton);
            modal.appendChild(modalContent);
            
            document.body.appendChild(modal);
        });
    });
}

// Fetch analytics data from the backend
async function loadAnalyticsData() {
    try {
        const response = await fetch('http://localhost:5000/api/analytics');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        updateDashboard(data);
        
    } catch (error) {
        console.error('Error loading analytics data:', error);
        showErrorMessage();
    }
}

// Update the dashboard with the fetched data
function updateDashboard(data) {
    // Update summary metrics
    const totalQueries = data.categories.reduce((sum, category) => sum + category.count, 0);
    document.getElementById('totalQueries').textContent = totalQueries;
    
    const satisfactionRate = data.satisfaction !== null ? 
        `${(data.satisfaction * 100).toFixed(1)}%` : 'No data';
    document.getElementById('satisfactionRate').textContent = satisfactionRate;
    
    const fallbackRate = `${data.fallback_rate.toFixed(1)}%`;
    document.getElementById('fallbackRate').textContent = fallbackRate;
    
    // Estimate feedback count (this is an approximation)
    const feedbackCount = data.satisfaction !== null ? 
        Math.round(totalQueries * 0.4) : '0'; // Assuming 40% of queries received feedback
    document.getElementById('feedbackCount').textContent = feedbackCount;
    
    // Update question categories chart
    updateCategoriesChart(data.categories);
    
    // Create mock satisfaction data (since we don't have historical data in this implementation)
    const mockSatisfactionData = generateMockSatisfactionData(data.satisfaction);
    updateSatisfactionChart(mockSatisfactionData);
}

// Update the categories chart
function updateCategoriesChart(categories) {
    const categoriesContainer = document.getElementById('categoriesChart');
    const noCategoriesData = document.getElementById('noCategoriesData');
    
    if (categories.length === 0) {
        categoriesContainer.style.display = 'none';
        noCategoriesData.style.display = 'block';
        return;
    }
    
    categoriesContainer.style.display = 'block';
    noCategoriesData.style.display = 'none';
    
    const labels = categories.map(category => formatCategoryName(category.category));
    const counts = categories.map(category => category.count);
    const backgroundColors = generateColorArray(categories.length);
    
    if (categoriesChart) {
        categoriesChart.data.labels = labels;
        categoriesChart.data.datasets[0].data = counts;
        categoriesChart.data.datasets[0].backgroundColor = backgroundColors;
        categoriesChart.update();
    } else {
        categoriesChart = new Chart(categoriesContainer, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: backgroundColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

// Update the satisfaction chart
function updateSatisfactionChart(data) {
    const satisfactionContainer = document.getElementById('satisfactionChart');
    const noSatisfactionData = document.getElementById('noSatisfactionData');
    
    if (data.length === 0) {
        satisfactionContainer.style.display = 'none';
        noSatisfactionData.style.display = 'block';
        return;
    }
    
    satisfactionContainer.style.display = 'block';
    noSatisfactionData.style.display = 'none';
    
    const labels = data.map(item => item.date);
    const values = data.map(item => item.value * 100); // Convert to percentage
    
    if (satisfactionChart) {
        satisfactionChart.data.labels = labels;
        satisfactionChart.data.datasets[0].data = values;
        satisfactionChart.update();
    } else {
        satisfactionChart = new Chart(satisfactionContainer, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Satisfaction Rate (%)',
                    data: values,
                    borderColor: '#0a84ff',
                    backgroundColor: 'rgba(10, 132, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Satisfaction Rate (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    }
                }
            }
        });
    }
}

// Format category names for better display
function formatCategoryName(category) {
    // Convert snake_case or category names to Title Case
    return category
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Generate an array of colors for the chart
function generateColorArray(count) {
    const colors = [
        '#4285F4', // Blue
        '#EA4335', // Red
        '#FBBC05', // Yellow
        '#34A853', // Green
        '#FF6D01', // Orange
        '#46BDC6', // Teal
        '#7B1FA2', // Purple
        '#0097A7', // Cyan
        '#689F38', // Light Green
        '#F06292', // Pink
    ];
    
    // If we need more colors than in our predefined array, generate them
    if (count > colors.length) {
        for (let i = colors.length; i < count; i++) {
            const hue = (i * 137) % 360; // Use golden ratio for even distribution
            colors.push(`hsl(${hue}, 70%, 60%)`);
        }
    }
    
    return colors.slice(0, count);
}

// Generate mock satisfaction data for demonstration
function generateMockSatisfactionData(currentSatisfaction) {
    // If no satisfaction data, return empty array
    if (currentSatisfaction === null) {
        return [];
    }
    
    const data = [];
    const today = new Date();
    
    // Generate data for the last 7 days
    for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        
        // Format date as MM/DD
        const formattedDate = `${date.getMonth() + 1}/${date.getDate()}`;
        
        // Generate a value that trends toward the current satisfaction
        // with some random variation
        const baseValue = i === 0 ? currentSatisfaction : Math.random() * 0.3 + 0.6;
        const value = i === 0 ? currentSatisfaction : 
            (baseValue * 0.7) + (currentSatisfaction * 0.3) + (Math.random() * 0.1 - 0.05);
        
        data.push({
            date: formattedDate,
            value: Math.min(Math.max(value, 0), 1) // Ensure value is between 0 and 1
        });
    }
    
    return data;
}

// Show error message if data loading fails
function showErrorMessage() {
    document.getElementById('totalQueries').textContent = 'Error';
    document.getElementById('satisfactionRate').textContent = 'Error';
    document.getElementById('fallbackRate').textContent = 'Error';
    document.getElementById('feedbackCount').textContent = 'Error';
    
    document.getElementById('categoriesChart').style.display = 'none';
    document.getElementById('noCategoriesData').style.display = 'block';
    document.getElementById('noCategoriesData').textContent = 'Error loading data. Please try again.';
    
    document.getElementById('satisfactionChart').style.display = 'none';
    document.getElementById('noSatisfactionData').style.display = 'block';
    document.getElementById('noSatisfactionData').textContent = 'Error loading data. Please try again.';
}
