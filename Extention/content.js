// content.js
(function() {
    let processButton = null;

    function initialize() {
        if (processButton) return;
        createProcessButton();
    }

    function createProcessButton() {
        processButton = document.createElement('button');
        processButton.id = 'process-reel-button';
        processButton.textContent = 'Process Reel';
        processButton.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;

        processButton.addEventListener('mouseover', () => {
            processButton.style.backgroundColor = '#45a049';
        });

        processButton.addEventListener('mouseout', () => {
            processButton.style.backgroundColor = '#4CAF50';
        });

        processButton.addEventListener('click', handleButtonClick);
        document.body.appendChild(processButton);
    }

    function handleButtonClick() {
        const reelUrl = window.location.href;
        
        processButton.disabled = true;
        processButton.style.backgroundColor = '#cccccc';
        processButton.textContent = 'Processing...';

        // Send message to background script using chrome.runtime.sendMessage
        chrome.runtime.sendMessage(
            { 
                action: 'processReel',
                url: reelUrl 
            },
            handleResponse
        );
    }
    
    function handleResponse(response) {
        processButton.disabled = false;
        processButton.style.backgroundColor = '#4CAF50';
        processButton.textContent = 'Process Reel';

        if (response && response.success) {
            showNotification(response.message || 'Success!', 'success');
        } else {
            showNotification(response.message || 'Processing failed. Please try again.', 'error');
        }
    }

    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px;
            border-radius: 4px;
            color: white;
            z-index: 10000;
            animation: fadeInOut 3s ease-in-out forwards;
        `;

        notification.style.backgroundColor = type === 'success' ? '#4CAF50' : '#f44336';
        notification.textContent = message;

        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeInOut {
                0% { opacity: 0; transform: translateY(-20px); }
                10% { opacity: 1; transform: translateY(0); }
                90% { opacity: 1; transform: translateY(0); }
                100% { opacity: 0; transform: translateY(-20px); }
            }
        `;
        document.head.appendChild(style);

        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})();