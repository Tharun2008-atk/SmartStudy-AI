/* =========================================
   SmartStudy AI - Premium Interactions
========================================= */

document.addEventListener("DOMContentLoaded", () => {

    /* -----------------------------------------
       PAGE LOAD ANIMATION
    ----------------------------------------- */

    document.body.classList.add("page-loaded");


    /* -----------------------------------------
       CARD 3D TILT
    ----------------------------------------- */

    const cards = document.querySelectorAll(".card");

    cards.forEach(card => {

        card.addEventListener("mousemove", (e) => {

            const rect = card.getBoundingClientRect();

            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX =
                ((y - centerY) / centerY) * -7;

            const rotateY =
                ((x - centerX) / centerX) * 7;

            card.style.transform =
                `perspective(900px)
                 rotateX(${rotateX}deg)
                 rotateY(${rotateY}deg)
                 translateY(-10px)
                 scale(1.02)`;

        });

        card.addEventListener("mouseleave", () => {

            card.style.transform =
                "perspective(900px) rotateX(0deg) rotateY(0deg) translateY(0) scale(1)";

        });

    });


    /* -----------------------------------------
       BUTTON MAGNETIC EFFECT
    ----------------------------------------- */

    const buttons = document.querySelectorAll(
        ".btn, .btn-primary, .btn-secondary, button"
    );

    buttons.forEach(button => {

        button.addEventListener("mousemove", (e) => {

            const rect = button.getBoundingClientRect();

            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;

            button.style.transform =
                `translate(${x * 0.12}px, ${y * 0.12}px)`;

        });

        button.addEventListener("mouseleave", () => {

            button.style.transform = "translate(0,0)";

        });

    });


    /* -----------------------------------------
       SCROLL REVEAL
    ----------------------------------------- */

    const revealElements = document.querySelectorAll(
        ".features, .card, .cta, .dashboard-card, .stat-card"
    );

    const observer = new IntersectionObserver(
        (entries) => {

            entries.forEach(entry => {

                if (entry.isIntersecting) {

                    entry.target.classList.add("show");

                    observer.unobserve(entry.target);

                }

            });

        },
        {
            threshold: 0.12
        }
    );

    revealElements.forEach(element => {

        element.classList.add("reveal");

        observer.observe(element);

    });


    /* -----------------------------------------
       NAVBAR SCROLL EFFECT
    ----------------------------------------- */

    const navbar = document.querySelector(".navbar");

    if (navbar) {

        window.addEventListener("scroll", () => {

            if (window.scrollY > 40) {

                navbar.classList.add("navbar-scrolled");

            } else {

                navbar.classList.remove("navbar-scrolled");

            }

        });

    }

});