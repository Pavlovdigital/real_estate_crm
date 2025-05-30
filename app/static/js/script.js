document.addEventListener('DOMContentLoaded', function() {
    console.log('Flask приложение загружено и готово!');

    // Theme Switcher Logic
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeIcon = document.getElementById('themeIcon');
    const htmlElement = document.documentElement; // Target <html> for data-bs-theme

    // Function to apply theme
    const applyTheme = (theme) => {
        htmlElement.setAttribute('data-bs-theme', theme);
        if (theme === 'dark') {
            themeIcon.classList.remove('bi-brightness-high-fill');
            themeIcon.classList.add('bi-moon-stars-fill');
        } else {
            themeIcon.classList.remove('bi-moon-stars-fill');
            themeIcon.classList.add('bi-brightness-high-fill');
        }
    };

    // Load saved theme from localStorage or default to 'light'
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    // Event listener for theme toggle button
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            let currentTheme = htmlElement.getAttribute('data-bs-theme');
            let newTheme = currentTheme === 'light' ? 'dark' : 'light';
            applyTheme(newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // Example: Dismiss alerts after some time (Bootstrap 5 method)
    const alertList = document.querySelectorAll('.alert-dismissible');
    alertList.forEach(function (alertEl) {
        // Ensure Bootstrap's Alert component is available
        if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
            // No automatic dismissal, but this is how you'd manually initialize if needed for other JS interactions.
            // new bootstrap.Alert(alertEl); // This line is not for auto-dismissal
        }
    });

    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            // Check if the element is still in the DOM and bootstrap is loaded
            if (message && typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                 const alertInstance = bootstrap.Alert.getInstance(message);
                 if (alertInstance) {
                    alertInstance.close();
                 } else {
                    // Fallback if instance not found but element exists
                    // (e.g. if it was dynamically added and not initialized by Bootstrap)
                    // However, for simple auto-hide, direct removal or hiding is also an option.
                    // For now, relying on Bootstrap's close method if available.
                 }
            } else if (message && message.parentNode) { // Fallback if bootstrap not fully loaded or element is simple
                // message.style.display = 'none'; // Simple hide
            }
        }, 5000);
    });

});
