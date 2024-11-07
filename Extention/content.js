(function() {
    let processButton = null;

    function initialize() {
        observeDOM();
    }

    function observeDOM() {
        // Target the main container where Instagram dynamically loads content
        const targetNode = document.body;

        // Options for the observer (watch for child nodes and subtree changes)
        const config = { childList: true, subtree: true };

        // Callback function to execute when mutations are observed
        const callback = function(mutationsList, observer) {
            for (const mutation of mutationsList) {
                if (mutation.type === 'childList') {
                    addProcessButtonToReels();
                }
            }
        };

        // Create an observer instance
        const observer = new MutationObserver(callback);

        // Start observing the target node
        observer.observe(targetNode, config);

        // Initial check
        addProcessButtonToReels();
    }

    function addProcessButtonToReels() {
        // Adjust this selector to target Instagram's reel video elements
        const videoElements = document.querySelectorAll('video');

        videoElements.forEach(video => {
            const parentContainer = video.parentElement;

            if (!parentContainer || parentContainer.querySelector('#process-reel-button')) {
                return; // Skip if the button already exists
            }

            createProcessButton(parentContainer, video);
        });
    }

    function createProcessButton(container, video) {
        const button = document.createElement('button');
        button.id = 'process-reel-button';
        button.textContent = 'Process Reel';
        button.style.cssText = `
            position: absolute;
            top: 10px;
            left: 10px;
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

        button.addEventListener('mouseover', () => {
            button.style.backgroundColor = '#45a049';
        });

        button.addEventListener('mouseout', () => {
            button.style.backgroundColor = '#4CAF50';
        });

        button.addEventListener('click', () => handleButtonClick(video));

        // Ensure the container is positioned relative
        container.style.position = 'relative';
        container.appendChild(button);
    }

    function handleButtonClick(video) {
        const reelUrl = window.location.href;

        const button = video.parentElement.querySelector('#process-reel-button');
        button.disabled = true;
        button.style.backgroundColor = '#cccccc';
        button.textContent = 'Processing...';

        chrome.runtime.sendMessage(
            {
                action: 'processReel',
                url: reelUrl,
            },
            response => handleResponse(response, button)
        );
    }

    function handleResponse(response, button) {
        button.disabled = false;
        button.style.backgroundColor = '#4CAF50';
        button.textContent = 'Process Reel';

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
