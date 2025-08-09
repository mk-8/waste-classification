const API_URL = "https://xsj4irg98h.execute-api.us-east-1.amazonaws.com/predict";

// Your global variables
var USER_SELECTED_LABEL_ANSWER_CHOICE = "";
var USER_SELECTED_LABEL_BOOLEAN = "";
// <-- ADD THIS TO STORE THE IMAGE NAME
let IMAGE_NAME_FROM_PYTHON = "";
let predictionHasBeenMade = false;
// Capture the actual image_name from backend


function uploadImage() {
    // This check is a good idea from your previous code, let's add it back
    if (predictionHasBeenMade) {
        location.reload();
        return;
    }
    
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    const resultBox = document.getElementById('result');
    const previewBox = document.getElementById('preview');

    if (!file) {
        alert("Please select an image first.");
        return;
    }

    resultBox.innerHTML = "⏳ Predicting...";
    previewBox.innerHTML = "";

    const formData = new FormData();
    formData.append("file", file);

    fetch(API_URL, {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultBox.innerHTML = `❌ Error: ${data.error}`;
            return;
        }

        // --- CAPTURE THE IMAGE NAME ---
        IMAGE_NAME_FROM_PYTHON = data.image_name; // <-- FIX: Capture the correct name
        predictionHasBeenMade = true; // Set the flag to enable reload on next click

        resultBox.innerHTML = `
            <hr>
            <h3>Prediction Result</h3>
            <p><strong>Class:</strong> ${data.class_name}</p>
            <p><strong>Confidence:</strong> ${(data.confidence * 100).toFixed(2)}%</p>
            <form></form>
        `;

        askQuestion1();

        const reader = new FileReader();
        reader.onload = function(e) {
            previewBox.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
        };
        reader.readAsDataURL(file);
    })
    .catch(err => {
        console.error(err);
        resultBox.innerHTML = "❌ An error occurred while predicting.";
    });
}

function askQuestion1() {
    // ... no changes needed in this function
    const form = document.querySelector('#result form');
    if (!form) return;

    form.innerHTML = `
        <p style="margin-top: 15px;">Was the prediction correct?</p>
        <button type="button" class="feedback-btn">Yes</button>
        <button type="button" class="feedback-btn">No</button>
    `;

    form.querySelectorAll('.feedback-btn').forEach(button => {
        button.addEventListener('click', handleAnswer1);
    });
}

function handleAnswer1(event) {
    const answer = event.target.textContent;
    const form = document.querySelector('#result form');
    if (!form) return;

    if (answer === 'Yes') {
        USER_SELECTED_LABEL_BOOLEAN = "True";
        USER_SELECTED_LABEL_ANSWER_CHOICE = "NA";
        form.innerHTML = "<p>Thank you for confirming!</p>";
        main(); 
    } else {
        USER_SELECTED_LABEL_BOOLEAN = "False";
        askQuestion2();
    }
}

function askQuestion2() {
    const form = document.querySelector('#result form');
    if (!form) return;
    
    // Define the 10 choices
    const choices = ['Cardboard', 'Food','Glass','Metal','Miscellaneous','Paper','Plastic','Textile','Vegetation', 'None of these'];


    // Create a button for each choice
    let buttonsHTML = choices.map(choice => {
        return `<button type="button" class="choice-btn">${choice}</button>`;
    }).join('');

    form.innerHTML = `
        <p style="margin-top: 15px;">What was the correct item?</p>
        <div class="choices-grid">${buttonsHTML}</div>
    `;

    // Add listeners to all the new choice buttons
    document.querySelectorAll('.choice-btn').forEach(button => {
        button.addEventListener('click', handleAnswer2);
    });
}

function handleAnswer2(event) {
    const choice = event.target.textContent;
    USER_SELECTED_LABEL_ANSWER_CHOICE = choice;
    const form = document.querySelector('#result form');
    if (!form) return;
    form.innerHTML = "<p>Thank you for your feedback!</p>";
    main(); 
}

async function main() {
    // --- SEND THE IMAGE NAME TO THE BACKEND ---
    console.log("Sending feedback to backend:", { IMAGE_NAME_FROM_PYTHON, USER_SELECTED_LABEL_BOOLEAN, USER_SELECTED_LABEL_ANSWER_CHOICE });

    try {
        // --- FIX: Use the full URL for your Python server ---
        const response = await fetch('https://xsj4irg98h.execute-api.us-east-1.amazonaws.com/save-feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image_name: IMAGE_NAME_FROM_PYTHON, // <-- FIX: Send the image_name
                user_selected_label_boolean: USER_SELECTED_LABEL_BOOLEAN,
                user_selected_label_answer_choice: USER_SELECTED_LABEL_ANSWER_CHOICE
            }),
        });

        if (!response.ok) {
            // The response from the server wasn't good, log it for debugging
            const errorData = await response.json();
            console.error("Failed to save feedback. Server responded with:", errorData.detail);
        } else {
            const result = await response.json();
            console.log("Feedback saved:", result);
        }
    } catch (error) {
        console.error("Error sending feedback:", error);
    }
}