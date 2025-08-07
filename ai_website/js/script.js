// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();

        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Observe sections for adding active class to navigation links
const sections = document.querySelectorAll('section');
const navLinks = document.querySelectorAll('nav ul li a');

const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            navLinks.forEach(link => {
                link.classList.remove('active');
            });
            const id = entry.target.getAttribute('id');
            document.querySelector(`nav ul li a[href="#${id}"]`).classList.add('active');
        }
    });
}, {
    threshold: 0.5 // Adjust threshold as needed
});

sections.forEach(section => {
    observer.observe(section);
});

// Simple scroll animation for elements (example)
const elementsToAnimate = document.querySelectorAll('.service-card, .product-card, .about-content');

const scrollObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-in'); // Add a class to trigger animation
            scrollObserver.unobserve(entry.target); // Stop observing once animated
        }
    });
}, {
    threshold: 0.2 // Adjust threshold as needed
});

elementsToAnimate.forEach(element => {
    scrollObserver.observe(element);
});
