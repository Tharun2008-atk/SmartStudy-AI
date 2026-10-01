
/* =========================================
SMARTSTUDY AI - ANIMATION SYSTEM
========================================= */

document.addEventListener("DOMContentLoaded", () => {

// Page entrance
const page = document.querySelector(".page-content");

if (page) {
page.classList.add("page-enter");
}


// Premium buttons
document.querySelectorAll("button").forEach(button => {
if (!button.classList.contains("no-animation")) {
button.classList.add("premium-button");
}
});


// AI forms
document.querySelectorAll("form").forEach(form => {

form.addEventListener("submit", () => {

const button = form.querySelector(
"button[type='submit']"
);

if (!button) return;

button.disabled = true;

button.classList.add("ai-loading");

const originalText = button.innerHTML;

button.dataset.originalText = originalText;

if (
originalText.toLowerCase().includes("note")
) {
button.innerHTML = "⏳ Generating Notes...";
}
else if (
originalText.toLowerCase().includes("quiz")
) {
button.innerHTML = "⏳ Generating Quiz...";
}
else if (
originalText.toLowerCase().includes("summary")
) {
button.innerHTML = "⏳ Creating Summary...";
}
else {
button.innerHTML = "⏳ Processing...";
}

});

});


// Animate elements when visible
const observer = new IntersectionObserver(
entries => {

entries.forEach(entry => {

if (entry.isIntersecting) {
entry.target.classList.add("slide-up");
observer.unobserve(entry.target);
}

});

},
{
threshold: 0.12
}
);


document
.querySelectorAll(".tool-card, .result-card, .feature-card")
.forEach(element => {

observer.observe(element);

});

});
