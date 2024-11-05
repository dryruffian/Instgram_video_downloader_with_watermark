// background.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'processReel') {
        processVideo(request.url, sendResponse);
        return true; // Keep message channel open for async response
    }
});

async function processVideo(reelUrl, sendResponse) {
    try {
        const response = await fetch('http://127.0.0.1:5000/process_video', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ instagram_url: reelUrl })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const blob = await response.blob();
        const arrayBuffer = await blob.arrayBuffer();
        const fileBlob = new Blob([arrayBuffer], { type: 'video/mp4' });
        const fileUrl = URL.createObjectURL(fileBlob);

        chrome.downloads.download({
            url: fileUrl,
            filename: 'watermarked_video.mp4',
            saveAs: true
        }, (downloadId) => {
            if (chrome.runtime.lastError || !downloadId) {
                sendResponse({ 
                    success: false, 
                    message: `Download failed: ${chrome.runtime.lastError?.message || "Unknown error"}` 
                });
            } else {
                sendResponse({ 
                    success: true, 
                    message: 'Video processed and downloading.' 
                });
            }
            // Clean up the blob URL
            URL.revokeObjectURL(fileUrl);
        });
    } catch (error) {
        console.error('Error:', error);
        sendResponse({ 
            success: false, 
            message: `Error processing video: ${error.message}` 
        });
    }
}
