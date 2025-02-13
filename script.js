async function processTask() {
    const taskInput = document.getElementById("taskInput");
    const chatBox = document.getElementById("chatBox");

    const userMessage = document.createElement("div");
    userMessage.classList.add("message", "user-message");
    userMessage.innerText = taskInput.value;
    chatBox.appendChild(userMessage);
    
    const loadingMessage = document.createElement("div");
    loadingMessage.classList.add("message", "bot-message");
    loadingMessage.innerText = "Thinking...";
    chatBox.appendChild(loadingMessage);

    try {
        const response = await fetch("http://127.0.0.1:8000/process-request/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ name: taskInput.value }),
        });

        const data = await response.json();
        chatBox.removeChild(loadingMessage);

        const botMessage = document.createElement("div");
        botMessage.classList.add("message", "bot-message");

        if (data.status === "success") {
            botMessage.innerHTML = `<strong>${data.task_name}</strong>`;
            
            const productContainer = document.createElement("div");
            productContainer.classList.add("product-container");

            data.items.forEach(item => {
                const productCard = createProductCard(item);
                productContainer.appendChild(productCard);
            });

            botMessage.appendChild(productContainer);
        } else {
            botMessage.innerText = "Error: " + data.message;
        }

        chatBox.appendChild(botMessage);
    } catch (error) {
        chatBox.removeChild(loadingMessage);
        const errorMessage = document.createElement("div");
        errorMessage.classList.add("message", "bot-message");
        errorMessage.innerText = "Network error: " + error.message;
        chatBox.appendChild(errorMessage);
    }

    taskInput.value = "";
}

function createProductCard(item) {
    const card = document.createElement("div");
    card.classList.add("product-card");

    const name = document.createElement("div");
    name.classList.add("product-name");
    name.textContent = item.name;

    const weight = document.createElement("div");
    weight.classList.add("product-weight");
    weight.textContent = `${item.quantity || "1"} ${item.units || "piece"}`;

    const quantityControls = document.createElement("div");
    quantityControls.classList.add("quantity-controls");

    const decreaseBtn = document.createElement("button");
    decreaseBtn.classList.add("quantity-btn");
    decreaseBtn.textContent = "-";
    
    const quantityDisplay = document.createElement("span");
    quantityDisplay.classList.add("quantity-display");
    quantityDisplay.textContent = "1";
    
    const increaseBtn = document.createElement("button");
    increaseBtn.classList.add("quantity-btn");
    increaseBtn.textContent = "+";

    // Add event listeners for quantity controls
    let quantity = 1;
    decreaseBtn.addEventListener("click", () => {
        if (quantity > 1) {
            quantity--;
            quantityDisplay.textContent = quantity;
        }
    });

    increaseBtn.addEventListener("click", () => {
        quantity++;
        quantityDisplay.textContent = quantity;
    });

    quantityControls.appendChild(decreaseBtn);
    quantityControls.appendChild(quantityDisplay);
    quantityControls.appendChild(increaseBtn);

    card.appendChild(name);
    card.appendChild(weight);
    card.appendChild(quantityControls);

    return card;
}
