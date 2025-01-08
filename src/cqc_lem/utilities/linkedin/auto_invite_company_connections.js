

// Global constant to control debugging
const DEBUG = true;

// Utility function for debugging
function debugLog(message) {
    if (DEBUG) {
        console.log(message);
    }
}

// Function to get available credits
function getAvailableCredits() {
    debugLog("Entering getAvailableCredits function.");
    
	const creditTextElement = document.evaluate('//span[text()[contains(.,"credits available")]]/span', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
	const creditText = creditTextElement.textContent;
    
    const [currentCredits, totalCredits] = creditText.split('/').map(Number);
    
    debugLog(`Credits available: ${currentCredits}/${totalCredits}`);
    
    return {
        currentCredits,
        totalCredits
    };
}

// Function to get the initial count of already selected checkboxes
function getInitialSelectedCount() {
    debugLog("Entering getInitialSelectedCount function.");
    
	const selectedTextElement = 	document.evaluate('//span[text()[contains(.,"selected")]]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
	
	const selectedText = selectedTextElement.textContent.trim();
	const initialSelectedCount = parseInt(selectedText.match(/\d+/)[0], 10);
	
    
    debugLog(`Initial selected count: ${initialSelectedCount}`);
    
    return isNaN(initialSelectedCount) ? 0 : initialSelectedCount;
}

// Function to scroll the invitee list once to load more connections
function scrollInviteeList(scrollElement, callback) {
    debugLog("Entering scrollInviteeList function.");
    
    const currentHeight = scrollElement.scrollHeight;
    scrollElement.scrollTop = currentHeight;
	
	scrollElement.scrollIntoView(false) // Move the bottom of the element into view
    
    debugLog("Scrolled down to load more connections.");
    
    // Wait for the AJAX request to load more connections
    setTimeout(() => {
        debugLog("Completed scrollInviteeList function, invoking callback.");
        callback();
    }, 2000);
}

// Function to select checkboxes for the connections
function selectConnectionCheckboxes(limit, scrollElement, callback) {
    debugLog("Entering selectConnectionCheckboxes function.");
    
    const xpath = "//input[@type='checkbox' and contains(@id, 'invitee')]";
    const checkboxes = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);

    let selectedCount = getInitialSelectedCount();
    debugLog(`Starting with selectedCount = ${selectedCount}`);

    for (let i = 0; i < checkboxes.snapshotLength && selectedCount < limit; i++) {
        const checkbox = checkboxes.snapshotItem(i);
        if (!checkbox.checked) {
            checkbox.click();
            debugLog(`Checkbox ${checkbox.id} selected.`);
            selectedCount++;
        }
    }

    if (selectedCount < limit && checkboxes.snapshotLength < limit) {
        debugLog(`Selected ${selectedCount} connections so far. Scrolling to load more...`);
        scrollInviteeList(scrollElement, () => {
            selectConnectionCheckboxes(limit, scrollElement, callback);
        });
    } else {
        debugLog(`Completed selecting checkboxes with selectedCount = ${selectedCount}`);
        callback(selectedCount);
    }
}

// Function to invite selected connections
function inviteSelectedConnections() {
    debugLog("Entering inviteSelectedConnections function.");
    
    const xpath = "//div[contains(@class,'modal')]//button[contains(@class,'artdeco-button--primary')]";
    const inviteButton = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    if (inviteButton) {
		const inviteButtonFinal = checkboxes.snapshotItem(0);
    	if (inviteButtonFinal) {
        	inviteButton.click();
        	debugLog("Invite button clicked.");
    	} else {
        	debugLog("Invite button not found.");
   		}
	} else {
        	debugLog("Invite button not found.");
   		}
}

// Function to dismiss the "No thanks" prompt if it appears
function dismissPrompt() {
    debugLog("Entering dismissPrompt function.");
    
    const dismissButton = document.querySelector("button[data-test-org-post-nudge-dismiss-cta]");
    if (dismissButton) {
        dismissButton.click();
        debugLog('"No thanks" button clicked.');
        return true;  // Return true to indicate the prompt was handled
    }
    
    debugLog("No 'No thanks' button found.");
    return false;  // Return false if there was no prompt to handle
}

// Function to automate the entire process
function automateInvitations() {
    debugLog("Entering automateInvitations function.");
    
    const { currentCredits } = getAvailableCredits();

    if (currentCredits <= 0) {
        debugLog("No credits available. Exiting automateInvitations.");
        return;
    }

    const inviteeListElement_old = document.querySelector(".invitee-picker-content__results-list");
	
	const inviteeListElement = document.querySelector(".scaffold-finite-scroll__content");
	
	selectConnectionCheckboxes(currentCredits, inviteeListElement, (selectedCount) => {
        if (selectedCount > 0) {
            inviteSelectedConnections();

            // Delay to ensure the prompt appears before checking for it
            setTimeout(() => {
                const promptHandled = dismissPrompt();
                if (promptHandled) {
                    debugLog("Prompt handled, continuing with automateInvitations.");
                    setTimeout(automateInvitations, 2000);
                } else {
                    debugLog("No prompt to handle, continuing with automateInvitations.");
                    automateInvitations();
                }
            }, 2000);
        } else {
            debugLog("No more connections to invite or already selected. Exiting automateInvitations.");
            return;
        }
    });
}

// Start the process
debugLog("Starting the LinkedIn connection automation process.");
automateInvitations();

//const inviteeListElement = document.querySelector(".scaffold-finite-scroll__content");
//selectConnectionCheckboxes(50,inviteeListElement,()=>{})
