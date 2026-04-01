document.addEventListener('DOMContentLoaded', () => {
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.2
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            } else {
                entry.target.classList.remove('visible');
            }
        });
    }, observerOptions);

    const animatedElements = document.querySelectorAll('.fade-up, .slide-in-left, .slide-in-right');
    animatedElements.forEach(el => observer.observe(el));

    // Full-page scrolling logic
    let currentSectionIndex = 0;
    const sections = document.querySelectorAll('.hero, .feature-section');
    let isScrolling = false;

    function scrollToSection(index) {
        if (index < 0 || index >= sections.length) return;
        isScrolling = true;
        currentSectionIndex = index;
        sections[currentSectionIndex].scrollIntoView({ behavior: 'smooth' });
        
        // Unlock after animation
        setTimeout(() => {
            isScrolling = false;
        }, 1000);
    }

    window.addEventListener('wheel', (e) => {
        e.preventDefault(); // Block default scroll
        if (isScrolling) return;

        if (e.deltaY > 0) {
            scrollToSection(currentSectionIndex + 1);
        } else if (e.deltaY < 0) {
            scrollToSection(currentSectionIndex - 1);
        }
    }, { passive: false });

    let touchStartY = 0;
    
    window.addEventListener('touchstart', e => {
        touchStartY = e.changedTouches[0].screenY;
    }, { passive: false });

    window.addEventListener('touchmove', e => {
        e.preventDefault(); 
    }, { passive: false });

    window.addEventListener('touchend', e => {
        if (isScrolling) return;
        let touchEndY = e.changedTouches[0].screenY;
        
        if (touchStartY - touchEndY > 50) {
            scrollToSection(currentSectionIndex + 1);
        } else if (touchEndY - touchStartY > 50) {
            scrollToSection(currentSectionIndex - 1);
        }
    }, { passive: false });
});
