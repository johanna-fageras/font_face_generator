let customWeights = {};

// Load weight mappings on page load
fetch("/api/weights")
  .then((response) => response.json())
  .then((weights) => {
    const weightMappings = document.getElementById("weightMappings");
    const formattedText = weights
      .map(([name, value]) => `${name} (${value})`)
      .join("\n");
    weightMappings.textContent = formattedText;
  });

// Load custom weights if they exist
fetch("/api/custom-weights")
  .then((response) => response.json())
  .then((weights) => {
    customWeights = weights;
    updateCustomWeightsList();
  })
  .catch(() => {
    customWeights = {};
    updateCustomWeightsList();
  });

// Handle adding custom weights
document.getElementById("addWeight").addEventListener("click", async (e) => {
  e.preventDefault();

  const name = document.getElementById("weightName").value.trim();
  const value = document.getElementById("weightValue").value.trim();

  if (!name || !value) {
    alert("Please enter both weight name and value");
    return;
  }

  if (!/^\d+$/.test(value)) {
    alert("Weight value must be a number");
    return;
  }

  customWeights[name] = value;
  await saveCustomWeights();

  // Clear inputs
  document.getElementById("weightName").value = "";
  document.getElementById("weightValue").value = "";

  // Refresh weight mappings
  const weightsResponse = await fetch("/api/weights");
  const weights = await weightsResponse.json();
  const weightMappings = document.getElementById("weightMappings");
  const formattedText = weights
    .map(([name, value]) => `${name}: ${value}`)
    .join(", ");
  weightMappings.textContent = formattedText;
});

function updateCustomWeightsList() {
  const list = document.getElementById("customWeightsList");
  list.innerHTML = "";

  Object.entries(customWeights).forEach(([name, value]) => {
    const row = document.createElement("div");
    row.className = "row mb-2";
    row.innerHTML = `
      <div class="col">${name}</div>
      <div class="col">${value}</div>
      <div class="col-auto">
        <button class="btn btn-sm btn-danger" onclick="removeWeight('${name}')">Remove</button>
      </div>
    `;
    list.appendChild(row);
  });
}

async function removeWeight(name) {
  delete customWeights[name];
  await saveCustomWeights();

  // Refresh both the custom list and default mappings
  updateCustomWeightsList();
  const weightsResponse = await fetch("/api/weights");
  const weights = await weightsResponse.json();
  const weightMappings = document.getElementById("weightMappings");
  const formattedText = weights
    .map(([name, value]) => `${name}: ${value}`)
    .join(", ");
  weightMappings.textContent = formattedText;
}

async function saveCustomWeights() {
  try {
    const response = await fetch("/api/custom-weights", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(customWeights),
    });

    if (!response.ok) {
      throw new Error("Failed to save custom weights");
    }

    updateCustomWeightsList();
  } catch (error) {
    alert("Error saving custom weights: " + error.message);
  }
}

// Handle CSS generation form
document
  .getElementById("generateForm")
  .addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData();
    const files = document.getElementById("fontFiles").files;

    for (let file of files) {
      formData.append("files[]", file);
    }

    formData.append("fontFamily", document.getElementById("fontFamily").value);
    formData.append("baseUrl", document.getElementById("baseUrl").value);
    formData.append(
      "useCustomWeights",
      document.getElementById("useCustomWeights").checked
    );

    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      document.getElementById("cssOutput").textContent = result.css;
      document.getElementById("downloadBtn").disabled = false;

      // Store for download
      window.generatedCSS = {
        content: result.css,
        filename: result.filename,
      };
    } catch (error) {
      alert("Error generating CSS: " + error.message);
    }
  });

// Handle download button
document.getElementById("downloadBtn").addEventListener("click", async () => {
  if (!window.generatedCSS) return;

  try {
    const response = await fetch("/api/download", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        css: window.generatedCSS.content,
        filename: window.generatedCSS.filename,
      }),
    });

    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = window.generatedCSS.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } else {
      throw new Error("Download failed");
    }
  } catch (error) {
    alert("Error downloading CSS: " + error.message);
  }
});
