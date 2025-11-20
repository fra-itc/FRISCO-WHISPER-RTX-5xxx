/**
 * FRISCO WHISPER RTX 5xxx - Client-Side JavaScript
 * Handles file uploads, real-time updates, and UI interactions
 */

// ============================================================================
// Toast Notifications
// ============================================================================

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, error, info)
 * @param {number} duration - Duration in milliseconds
 */
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = type === 'success' ? 'fa-check-circle' :
                 type === 'error' ? 'fa-times-circle' :
                 'fa-info-circle';

    toast.innerHTML = `
        <i class="fas ${icon}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Auto-remove after duration
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Add slideOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ============================================================================
// API Helper Functions
// ============================================================================

/**
 * Make API request with error handling
 * @param {string} url - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise<any>} Response data
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format date string
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    // Less than 1 hour ago
    if (diffMins < 60) {
        return diffMins === 0 ? 'Just now' : `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    }

    // Less than 24 hours ago
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) {
        return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    }

    // Less than 7 days ago
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) {
        return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    }

    // Format as date
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format file size in bytes to human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

/**
 * Format duration in seconds to human-readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration
 */
function formatDuration(seconds) {
    if (!seconds || seconds < 0) return 'N/A';

    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    }

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    if (minutes < 60) {
        return remainingSeconds > 0
            ? `${minutes}m ${remainingSeconds}s`
            : `${minutes}m`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    return remainingMinutes > 0
        ? `${hours}h ${remainingMinutes}m`
        : `${hours}h`;
}

/**
 * Get status icon for job status
 * @param {string} status - Job status
 * @returns {string} HTML for icon
 */
function getStatusIcon(status) {
    const icons = {
        'pending': '<i class="fas fa-clock"></i>',
        'processing': '<i class="fas fa-spinner fa-spin"></i>',
        'completed': '<i class="fas fa-check-circle"></i>',
        'failed': '<i class="fas fa-times-circle"></i>',
        'cancelled': '<i class="fas fa-ban"></i>'
    };
    return icons[status] || '<i class="fas fa-question-circle"></i>';
}

/**
 * Debounce function to limit function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Validate audio file
 * @param {File} file - File to validate
 * @returns {object} Validation result
 */
function validateAudioFile(file) {
    const allowedExtensions = ['.mp3', '.wav', '.m4a', '.mp4', '.aac', '.flac', '.opus'];
    const maxSize = 500 * 1024 * 1024; // 500MB

    const extension = '.' + file.name.split('.').pop().toLowerCase();

    if (!allowedExtensions.includes(extension)) {
        return {
            valid: false,
            error: `Invalid file type. Allowed formats: ${allowedExtensions.join(', ')}`
        };
    }

    if (file.size > maxSize) {
        return {
            valid: false,
            error: `File too large. Maximum size is ${formatFileSize(maxSize)}`
        };
    }

    return { valid: true };
}

// ============================================================================
// WebSocket Manager
// ============================================================================

class WebSocketManager {
    constructor() {
        this.connections = new Map();
    }

    /**
     * Connect to WebSocket for job updates
     * @param {string} jobId - Job ID to monitor
     * @param {Function} onMessage - Callback for messages
     * @param {Function} onError - Callback for errors
     */
    connect(jobId, onMessage, onError) {
        if (this.connections.has(jobId)) {
            return; // Already connected
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/jobs/${jobId}`;

        try {
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log(`WebSocket connected for job ${jobId}`);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    onMessage(data);

                    // Auto-close on completion or failure
                    if (data.type === 'status' && (data.status === 'completed' || data.status === 'failed')) {
                        setTimeout(() => this.disconnect(jobId), 1000);
                    }
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            ws.onerror = (error) => {
                console.error(`WebSocket error for job ${jobId}:`, error);
                if (onError) onError(error);
            };

            ws.onclose = () => {
                console.log(`WebSocket closed for job ${jobId}`);
                this.connections.delete(jobId);
            };

            this.connections.set(jobId, ws);

            // Send periodic pings to keep connection alive
            const pingInterval = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                } else {
                    clearInterval(pingInterval);
                }
            }, 15000);

        } catch (error) {
            console.error(`Failed to create WebSocket for job ${jobId}:`, error);
            if (onError) onError(error);
        }
    }

    /**
     * Disconnect WebSocket for job
     * @param {string} jobId - Job ID
     */
    disconnect(jobId) {
        const ws = this.connections.get(jobId);
        if (ws) {
            ws.close();
            this.connections.delete(jobId);
        }
    }

    /**
     * Disconnect all WebSockets
     */
    disconnectAll() {
        this.connections.forEach((ws, jobId) => {
            ws.close();
        });
        this.connections.clear();
    }
}

// Global WebSocket manager instance
const wsManager = new WebSocketManager();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    wsManager.disconnectAll();
});

// ============================================================================
// File Upload Handler
// ============================================================================

class FileUploadHandler {
    constructor() {
        this.currentFile = null;
        this.uploadProgress = 0;
    }

    /**
     * Upload file to server
     * @param {File} file - File to upload
     * @param {Function} onProgress - Progress callback
     * @returns {Promise<object>} Upload result
     */
    async upload(file, onProgress) {
        this.currentFile = file;
        this.uploadProgress = 0;

        const formData = new FormData();
        formData.append('file', file);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Progress tracking
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    this.uploadProgress = (e.loaded / e.total) * 100;
                    if (onProgress) {
                        onProgress({
                            loaded: e.loaded,
                            total: e.total,
                            percentage: this.uploadProgress
                        });
                    }
                }
            });

            // Success
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        reject(new Error('Failed to parse server response'));
                    }
                } else {
                    try {
                        const error = JSON.parse(xhr.responseText);
                        reject(new Error(error.detail || `Upload failed: ${xhr.status}`));
                    } catch {
                        reject(new Error(`Upload failed: ${xhr.status}`));
                    }
                }
            });

            // Error
            xhr.addEventListener('error', () => {
                reject(new Error('Network error during upload'));
            });

            // Abort
            xhr.addEventListener('abort', () => {
                reject(new Error('Upload cancelled'));
            });

            // Send request
            xhr.open('POST', '/api/v1/upload');
            xhr.send(formData);
        });
    }

    /**
     * Cancel current upload
     */
    cancel() {
        // Note: XHR needs to be stored as instance variable to cancel
        // For now, this is a placeholder
        console.log('Upload cancellation not implemented');
    }
}

// Global upload handler instance
const uploadHandler = new FileUploadHandler();

// ============================================================================
// Language Codes Mapping
// ============================================================================

const LANGUAGE_NAMES = {
    'en': 'English',
    'it': 'Italian',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish',
    'sv': 'Swedish',
    'no': 'Norwegian',
    'da': 'Danish',
    'fi': 'Finnish',
    'cs': 'Czech',
    'ro': 'Romanian',
    'uk': 'Ukrainian',
    'el': 'Greek',
    'he': 'Hebrew',
    'th': 'Thai',
    'vi': 'Vietnamese'
};

/**
 * Get language name from code
 * @param {string} code - Language code
 * @returns {string} Language name
 */
function getLanguageName(code) {
    return LANGUAGE_NAMES[code] || code || 'Unknown';
}

// ============================================================================
// Model Information
// ============================================================================

const MODEL_INFO = {
    'tiny': {
        name: 'Tiny',
        description: 'Fastest, least accurate',
        speed: 'Very Fast',
        accuracy: 'Low',
        vram: '~1 GB'
    },
    'base': {
        name: 'Base',
        description: 'Fast with decent accuracy',
        speed: 'Fast',
        accuracy: 'Medium',
        vram: '~1 GB'
    },
    'small': {
        name: 'Small',
        description: 'Balanced speed and accuracy',
        speed: 'Medium',
        accuracy: 'Good',
        vram: '~2 GB'
    },
    'medium': {
        name: 'Medium',
        description: 'Accurate but slower',
        speed: 'Slow',
        accuracy: 'Very Good',
        vram: '~5 GB'
    },
    'large-v3': {
        name: 'Large-v3',
        description: 'Most accurate, GPU recommended',
        speed: 'Very Slow',
        accuracy: 'Excellent',
        vram: '~10 GB'
    },
    'large-v2': {
        name: 'Large-v2',
        description: 'Previous version of large model',
        speed: 'Very Slow',
        accuracy: 'Excellent',
        vram: '~10 GB'
    }
};

/**
 * Get model information
 * @param {string} modelSize - Model size
 * @returns {object} Model info
 */
function getModelInfo(modelSize) {
    return MODEL_INFO[modelSize] || {
        name: modelSize,
        description: 'Unknown model',
        speed: 'Unknown',
        accuracy: 'Unknown',
        vram: 'Unknown'
    };
}

// ============================================================================
// Error Handler
// ============================================================================

/**
 * Handle and display error
 * @param {Error} error - Error object
 * @param {string} context - Error context
 */
function handleError(error, context = 'Operation') {
    console.error(`${context} failed:`, error);

    const message = error.message || 'An unexpected error occurred';
    showToast(`${context} failed: ${message}`, 'error', 5000);
}

// ============================================================================
// Local Storage Helper
// ============================================================================

const Storage = {
    /**
     * Save preference to local storage
     * @param {string} key - Preference key
     * @param {any} value - Preference value
     */
    save(key, value) {
        try {
            localStorage.setItem(`whisper_${key}`, JSON.stringify(value));
        } catch (error) {
            console.error('Failed to save preference:', error);
        }
    },

    /**
     * Load preference from local storage
     * @param {string} key - Preference key
     * @param {any} defaultValue - Default value if not found
     * @returns {any} Saved value or default
     */
    load(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(`whisper_${key}`);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Failed to load preference:', error);
            return defaultValue;
        }
    },

    /**
     * Remove preference from local storage
     * @param {string} key - Preference key
     */
    remove(key) {
        try {
            localStorage.removeItem(`whisper_${key}`);
        } catch (error) {
            console.error('Failed to remove preference:', error);
        }
    }
};

// ============================================================================
// Initialize User Preferences
// ============================================================================

function initializePreferences() {
    // Load saved model preference
    const savedModel = Storage.load('preferred_model');
    if (savedModel) {
        const modelSelect = document.getElementById('modelSize');
        if (modelSelect) {
            modelSelect.value = savedModel;
        }
    }

    // Load saved language preference
    const savedLanguage = Storage.load('preferred_language');
    if (savedLanguage) {
        const languageSelect = document.getElementById('language');
        if (languageSelect) {
            languageSelect.value = savedLanguage;
        }
    }

    // Load saved beam size preference
    const savedBeamSize = Storage.load('preferred_beam_size');
    if (savedBeamSize) {
        const beamSizeInput = document.getElementById('beamSize');
        if (beamSizeInput) {
            beamSizeInput.value = savedBeamSize;
            const beamSizeValue = document.getElementById('beamSizeValue');
            if (beamSizeValue) {
                beamSizeValue.textContent = savedBeamSize;
            }
        }
    }

    // Save preferences when changed
    const modelSelect = document.getElementById('modelSize');
    if (modelSelect) {
        modelSelect.addEventListener('change', (e) => {
            Storage.save('preferred_model', e.target.value);
        });
    }

    const languageSelect = document.getElementById('language');
    if (languageSelect) {
        languageSelect.addEventListener('change', (e) => {
            Storage.save('preferred_language', e.target.value);
        });
    }

    const beamSizeInput = document.getElementById('beamSize');
    if (beamSizeInput) {
        beamSizeInput.addEventListener('change', (e) => {
            Storage.save('preferred_beam_size', e.target.value);
        });
    }
}

// Initialize preferences on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePreferences);
} else {
    initializePreferences();
}

// ============================================================================
// Keyboard Shortcuts
// ============================================================================

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K: Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Escape: Close modals
    if (e.key === 'Escape') {
        const modal = document.getElementById('jobModal');
        if (modal && modal.style.display !== 'none') {
            modal.style.display = 'none';
        }
    }
});

// ============================================================================
// Export functions for use in HTML
// ============================================================================

// Make functions available globally
window.showToast = showToast;
window.apiRequest = apiRequest;
window.formatDate = formatDate;
window.formatFileSize = formatFileSize;
window.formatDuration = formatDuration;
window.getStatusIcon = getStatusIcon;
window.validateAudioFile = validateAudioFile;
window.wsManager = wsManager;
window.uploadHandler = uploadHandler;
window.getLanguageName = getLanguageName;
window.getModelInfo = getModelInfo;
window.handleError = handleError;
window.Storage = Storage;

// ============================================================================
// Console Welcome Message
// ============================================================================

console.log('%c🎙️ Frisco Whisper RTX 5xxx', 'font-size: 20px; font-weight: bold; color: #00ff41;');
console.log('%cGPU-accelerated transcription service', 'font-size: 12px; color: #00ff41;');
console.log('%cv1.3.0', 'font-size: 10px; color: #808080;');
console.log('');
console.log('WebSocket Manager:', wsManager);
console.log('Upload Handler:', uploadHandler);
console.log('');
console.log('API Documentation: /docs');
console.log('');
