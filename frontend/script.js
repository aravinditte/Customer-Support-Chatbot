let sessionId = generateSessionId();
// Store session ID in localStorage for history page
localStorage.setItem('chatSessionId', sessionId);
let lastChatId = null;

// Initialize the chat interface
document.addEventListener('DOMContentLoaded', function() {
    // Set up event listeners
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) sendBtn.addEventListener('click', sendMessage);

    const inputEl = document.getElementById('messageInput');
    if (inputEl) {
        inputEl.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        // Focus on input field
        inputEl.focus();
    }

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

// Generate a random session ID
function generateSessionId() {
    return 'session_' + Math.random().toString(36).substring(2, 15);
}

function getApiBase() {
    // Fallback to same-origin if config.js missing
    return (window && window.API_BASE_URL) ? window.API_BASE_URL : '';
}

// Send message to backend
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    if (!messageInput) return;

    const message = messageInput.value.trim();
    if (message === '') return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Clear input field
    messageInput.value = '';
    
    // Show typing indicator
    addTypingIndicator();
    
    try {
        // Send message to backend
        const response = await fetch(`${getApiBase()}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator();
        
        // Add assistant response to chat
        addMessageToChat('assistant', data.response, data.chat_id);
        lastChatId = data.chat_id;
        
    } catch (error) {
        console.error('Error:', error);
        
        // Remove typing indicator
        removeTypingIndicator();
        
        // Add error message
        addMessageToChat('assistant', 'Sorry, I encountered an error connecting to the server. Please check your connection and try again.');
    }
    
    // Scroll to bottom
    scrollToBottom();
}

// Add message to chat interface
function addMessageToChat(sender, message, chatId = null) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    // Create message element
    const messageElement = document.createElement('div');
    messageElement.className = `message ${sender}`;
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    const paragraph = document.createElement('p');
    paragraph.textContent = message;
    
    messageContent.appendChild(paragraph);
    messageElement.appendChild(messageContent);
    
    // Add feedback buttons for assistant messages
    if (sender === 'assistant' && chatId !== null) {
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback';
        
        const thumbsUpBtn = document.createElement('button');
        thumbsUpBtn.textContent = '👍';
        thumbsUpBtn.onclick = function() { provideFeedback(chatId, 1); };
        
        const thumbsDownBtn = document.createElement('button');
        thumbsDownBtn.textContent = '👎';
        thumbsDownBtn.onclick = function() { provideFeedback(chatId, 0); };
        
        feedbackDiv.appendChild(thumbsUpBtn);
        feedbackDiv.appendChild(thumbsDownBtn);
        
        messageContent.appendChild(feedbackDiv);
    }
    
    chatMessages.appendChild(messageElement);
    
    // Scroll to bottom
    scrollToBottom();
}

// Add typing indicator
function addTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    const indicatorElement = document.createElement('div');
    indicatorElement.className = 'message assistant typing-indicator';
    indicatorElement.id = 'typingIndicator';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    const paragraph = document.createElement('p');
    paragraph.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    
    messageContent.appendChild(paragraph);
    indicatorElement.appendChild(messageContent);
    
    chatMessages.appendChild(indicatorElement);
    
    // Scroll to bottom
    scrollToBottom();
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Scroll to bottom of chat
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send feedback to backend
async function provideFeedback(chatId, rating) {
    try {
        const response = await fetch(`${getApiBase()}/api/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: chatId,
                rating: rating
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Show feedback received message
        const feedbackElements = document.querySelectorAll('.feedback');
        feedbackElements.forEach(element => {
            element.innerHTML = '<span style="color: #888;">Thanks for your feedback!</span>';
        });
        
    } catch (error) {
        console.error('Error sending feedback:', error);
    }
}

// Function to ask predefined questions
function askQuestion(question) {
    const input = document.getElementById('messageInput');
    if (!input) return;
    input.value = question;
    sendMessage();
}
