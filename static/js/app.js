/**
 * Strava Activity Tracker - Frontend JavaScript
 * Handles activity fetching, map visualization, and user interactions
 */

class StravaActivityTracker {
    constructor() {
        this.map = null;
        this.activities = [];
        this.filteredActivities = [];
        this.currentPolyline = null;
        this.currentActivityId = null;
        
        this.init();
    }
    
    /**
     * Initialize the application
     */
    init() {
        this.initializeMap();
        this.bindEventListeners();
        this.loadActivities();
        this.loadStatistics();
    }
    
    /**
     * Initialize Leaflet map
     */
    initializeMap() {
        // Initialize map centered on France
        this.map = L.map('map').setView([46.603354, 1.888334], 6);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 18
        }).addTo(this.map);
        
        // Hide map initially
        document.getElementById('map').style.display = 'none';
    }
    
    /**
     * Bind event listeners
     */
    bindEventListeners() {
        // Refresh activities button
        document.getElementById('refresh-activities').addEventListener('click', () => {
            this.loadActivities(true);
        });
        
        // Activity type filter
        document.getElementById('activity-type-filter').addEventListener('change', (e) => {
            this.filterActivities(e.target.value);
        });
        
        // Window resize handler for map
        window.addEventListener('resize', () => {
            if (this.map) {
                setTimeout(() => {
                    this.map.invalidateSize();
                }, 100);
            }
        });
    }
    
    /**
     * Load activities from API
     */
    async loadActivities(forceRefresh = false) {
        const loadingElement = document.getElementById('activities-loading');
        const listElement = document.getElementById('activities-list');
        const noActivitiesElement = document.getElementById('no-activities');
        
        // Show loading state
        loadingElement.style.display = 'block';
        listElement.style.display = 'none';
        noActivitiesElement.style.display = 'none';
        
        try {
            const response = await fetch('/api/activities', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const activities = await response.json();
            this.activities = activities;
            this.filteredActivities = [...activities];
            
            this.renderActivities();
            
        } catch (error) {
            console.error('Error loading activities:', error);
            this.showError('Erreur lors du chargement des activités');
        } finally {
            loadingElement.style.display = 'none';
        }
    }
    
    /**
     * Load statistics from API
     */
    async loadStatistics() {
        const loadingElement = document.getElementById('stats-loading');
        const contentElement = document.getElementById('stats-content');
        
        try {
            const response = await fetch('/api/stats');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const stats = await response.json();
            
            // Update statistics display
            document.getElementById('total-activities').textContent = stats.total_activities;
            document.getElementById('total-distance').textContent = stats.total_distance_km;
            document.getElementById('total-time').textContent = stats.total_time_hours;
            document.getElementById('total-elevation').textContent = stats.total_elevation_m;
            
            // Update activity type filter with available types
            this.updateActivityTypeFilter(stats.activity_types);
            
            // Show statistics
            loadingElement.style.display = 'none';
            contentElement.style.display = 'block';
            
        } catch (error) {
            console.error('Error loading statistics:', error);
            loadingElement.style.display = 'none';
            contentElement.style.display = 'block';
        }
    }
    
    /**
     * Update activity type filter options
     */
    updateActivityTypeFilter(activityTypes) {
        const filterSelect = document.getElementById('activity-type-filter');
        const currentValue = filterSelect.value;
        
        // Clear existing options except "All types"
        while (filterSelect.children.length > 1) {
            filterSelect.removeChild(filterSelect.lastChild);
        }
        
        // Add options for each activity type
        Object.keys(activityTypes).forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = this.getActivityTypeLabel(type);
            filterSelect.appendChild(option);
        });
        
        // Restore previous selection if still valid
        if (currentValue && Object.keys(activityTypes).includes(currentValue)) {
            filterSelect.value = currentValue;
        }
    }
    
    /**
     * Get localized label for activity type
     */
    getActivityTypeLabel(type) {
        const labels = {
            'Run': 'Course à pied',
            'Ride': 'Vélo',
            'Walk': 'Marche',
            'Hike': 'Randonnée',
            'Swim': 'Natation',
            'Workout': 'Entraînement',
            'WeightTraining': 'Musculation',
            'Yoga': 'Yoga'
        };
        return labels[type] || type;
    }
    
    /**
     * Filter activities by type
     */
    filterActivities(type) {
        if (!type) {
            this.filteredActivities = [...this.activities];
        } else {
            this.filteredActivities = this.activities.filter(activity => activity.type === type);
        }
        
        this.renderActivities();
    }
    
    /**
     * Render activities list
     */
    renderActivities() {
        const listElement = document.getElementById('activities-list');
        const noActivitiesElement = document.getElementById('no-activities');
        
        if (this.filteredActivities.length === 0) {
            listElement.style.display = 'none';
            noActivitiesElement.style.display = 'block';
            return;
        }
        
        listElement.innerHTML = '';
        
        this.filteredActivities.forEach(activity => {
            const activityElement = this.createActivityElement(activity);
            listElement.appendChild(activityElement);
        });
        
        listElement.style.display = 'block';
        noActivitiesElement.style.display = 'none';
        
        // Add fade-in animation
        listElement.classList.add('fade-in');
    }
    
    /**
     * Create activity list item element
     */
    createActivityElement(activity) {
        const div = document.createElement('div');
        div.className = 'activity-item';
        div.dataset.activityId = activity.id;
        
        const typeClass = `type-${activity.type.toLowerCase()}`;
        
        div.innerHTML = `
            <div class="activity-type-badge ${typeClass}">
                ${this.getActivityTypeIcon(activity.type)} ${activity.type}
            </div>
            <div class="activity-name">${activity.name}</div>
            <div class="activity-meta">
                <i class="fas fa-calendar"></i> ${this.formatDate(activity.date)}
            </div>
            <div class="activity-stats">
                <div class="activity-stat">
                    <i class="fas fa-route"></i>
                    <span>${activity.distance_km} km</span>
                </div>
                <div class="activity-stat">
                    <i class="fas fa-clock"></i>
                    <span>${this.formatDuration(activity.duration_minutes)}</span>
                </div>
                <div class="activity-stat">
                    <i class="fas fa-mountain"></i>
                    <span>${activity.elevation_gain} m</span>
                </div>
                ${activity.average_speed > 0 ? `
                <div class="activity-stat">
                    <i class="fas fa-tachometer-alt"></i>
                    <span>${activity.average_speed} km/h</span>
                </div>
                ` : ''}
            </div>
        `;
        
        // Add click handler
        div.addEventListener('click', () => {
            this.selectActivity(activity);
        });
        
        return div;
    }
    
    /**
     * Get icon for activity type
     */
    getActivityTypeIcon(type) {
        const icons = {
            'Run': 'fas fa-running',
            'Ride': 'fas fa-bicycle',
            'Walk': 'fas fa-walking',
            'Hike': 'fas fa-hiking',
            'Swim': 'fas fa-swimmer',
            'Workout': 'fas fa-dumbbell',
            'WeightTraining': 'fas fa-weight-hanging',
            'Yoga': 'fas fa-leaf'
        };
        return `<i class="${icons[type] || 'fas fa-circle'}"></i>`;
    }
    
    /**
     * Format date for display
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    }
    
    /**
     * Format duration in minutes to readable format
     */
    formatDuration(minutes) {
        const hours = Math.floor(minutes / 60);
        const mins = Math.round(minutes % 60);
        
        if (hours > 0) {
            return `${hours}h${mins.toString().padStart(2, '0')}`;
        }
        return `${mins}min`;
    }
    
    /**
     * Select and display activity on map
     */
    async selectActivity(activity) {
        // Update UI selection
        document.querySelectorAll('.activity-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const activityElement = document.querySelector(`[data-activity-id="${activity.id}"]`);
        if (activityElement) {
            activityElement.classList.add('active');
        }
        
        // Update map title
        document.getElementById('map-title').innerHTML = `
            <i class="fas fa-map"></i> ${activity.name}
        `;
        
        // Load and display polyline
        await this.loadActivityPolyline(activity.id);
        
        this.currentActivityId = activity.id;
    }
    
    /**
     * Load and display activity polyline on map
     */
    async loadActivityPolyline(activityId) {
        try {
            const response = await fetch(`/api/activity/${activityId}/polyline`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.polyline) {
                this.displayPolylineOnMap(data.polyline, data);
            } else {
                this.showMapPlaceholder('Aucun tracé disponible pour cette activité');
            }
            
        } catch (error) {
            console.error('Error loading polyline:', error);
            this.showMapPlaceholder('Erreur lors du chargement du tracé');
        }
    }
    
    /**
     * Display polyline on map using Leaflet
     */
    displayPolylineOnMap(encodedPolyline, activityData) {
        try {
            // Decode polyline using the polyline library
            const coordinates = polyline.decode(encodedPolyline);
            
            // Convert to Leaflet format (lat, lng)
            const latLngs = coordinates.map(coord => [coord[0], coord[1]]);
            
            // Clear existing polyline
            if (this.currentPolyline) {
                this.map.removeLayer(this.currentPolyline);
            }
            
            // Create new polyline
            this.currentPolyline = L.polyline(latLngs, {
                color: '#fc4c02',
                weight: 3,
                opacity: 0.8
            }).addTo(this.map);
            
            // Fit map to polyline bounds
            this.map.fitBounds(this.currentPolyline.getBounds(), {
                padding: [20, 20]
            });
            
            // Add start marker if coordinates available
            if (activityData.start_latlng && activityData.start_latlng.length === 2) {
                const startIcon = L.divIcon({
                    className: 'start-marker',
                    html: '<i class="fas fa-play-circle" style="color: #28a745; font-size: 20px;"></i>',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });
                
                L.marker([activityData.start_latlng[0], activityData.start_latlng[1]], {
                    icon: startIcon
                }).addTo(this.map).bindPopup('Départ');
            }
            
            // Show map and hide placeholder
            document.getElementById('map').style.display = 'block';
            document.getElementById('map-placeholder').style.display = 'none';
            
            // Invalidate map size to ensure proper rendering
            setTimeout(() => {
                this.map.invalidateSize();
            }, 100);
            
        } catch (error) {
            console.error('Error displaying polyline:', error);
            this.showMapPlaceholder('Erreur lors de l\'affichage du tracé');
        }
    }
    
    /**
     * Show map placeholder with message
     */
    showMapPlaceholder(message = 'Sélectionnez une activité') {
        document.getElementById('map').style.display = 'none';
        document.getElementById('map-placeholder').style.display = 'flex';
        
        const placeholder = document.getElementById('map-placeholder');
        placeholder.innerHTML = `
            <div class="text-center">
                <i class="fas fa-map-marked-alt fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Carte</h5>
                <p class="text-muted">${message}</p>
            </div>
        `;
    }
    
    /**
     * Show error message
     */
    showError(message) {
        // Create error alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-custom fade-in';
        alert.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at top of sidebar
        const sidebar = document.querySelector('.sidebar-content');
        sidebar.insertBefore(alert, sidebar.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
    
    /**
     * Show success message
     */
    showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-custom fade-in';
        alert.innerHTML = `
            <i class="fas fa-check-circle"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const sidebar = document.querySelector('.sidebar-content');
        sidebar.insertBefore(alert, sidebar.firstChild);
        
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 3000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the authenticated page
    if (document.getElementById('map')) {
        window.stravaTracker = new StravaActivityTracker();
    }
});

// Handle page visibility changes to refresh data when user returns
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.stravaTracker) {
        // Refresh activities if page has been hidden for more than 5 minutes
        const lastRefresh = localStorage.getItem('lastActivityRefresh');
        const now = Date.now();
        
        if (!lastRefresh || (now - parseInt(lastRefresh)) > 300000) { // 5 minutes
            window.stravaTracker.loadActivities();
            localStorage.setItem('lastActivityRefresh', now.toString());
        }
    }
});
