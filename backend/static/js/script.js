document.getElementById("capture-button").addEventListener("click", function () {
    const button = this;

    // Disable the button to prevent multiple clicks
    button.disabled = true;
    button.textContent = "Processing...";

    // Make the POST request to capture the image
    fetch("/capture", { method: "POST" })
        .then(response => {
            if (response.redirected) {
                // Redirect to the result page
                window.location.href = response.url;
            } else if (response.ok) {
                // Handle non-redirected success cases (if applicable)
                console.log("Image captured successfully.");
            } else {
                throw new Error(`Server responded with status: ${response.status}`);
            }
        })
        .catch(error => {
            // Display error feedback
            console.error("Error capturing image:", error);
            alert("Failed to capture image. Please try again.");
        })
        .finally(() => {
            // Re-enable the button regardless of success or failure
            button.disabled = false;
            button.textContent = "Capture Image";
        });
});
