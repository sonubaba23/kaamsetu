document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  if (typeof gsap === "undefined") return;
  gsap.registerPlugin(ScrollTrigger);

  gsap.utils.toArray(".reveal").forEach((el, i) => {
    gsap.to(el, {
      opacity: 1,
      y: 0,
      duration: 0.8,
      delay: (i % 4) * 0.08,
      ease: "power3.out",
      scrollTrigger: {
        trigger: el,
        start: "top 88%",
        toggleActions: "play none none reverse",
      },
    });
  });

  gsap.utils.toArray(".glow-orb").forEach((orb, i) => {
    gsap.to(orb, {
      x: i % 2 === 0 ? 40 : -40,
      y: i % 2 === 0 ? -30 : 30,
      duration: 8 + i * 2,
      repeat: -1,
      yoyo: true,
      ease: "sine.inOut",
    });
  });

  gsap.utils.toArray("[data-counter]").forEach((el) => {
    const target = parseFloat(el.dataset.counter);
    const obj = { val: 0 };
    ScrollTrigger.create({
      trigger: el,
      start: "top 90%",
      once: true,
      onEnter: () => {
        gsap.to(obj, {
          val: target,
          duration: 1.6,
          ease: "power2.out",
          onUpdate: () => {
            el.textContent = Number.isInteger(target)
              ? Math.floor(obj.val).toLocaleString("en-IN")
              : obj.val.toFixed(1);
          },
        });
      },
    });
  });

  gsap.utils.toArray("[data-tilt]").forEach((card) => {
    card.addEventListener("mousemove", (e) => {
      const r = card.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      gsap.to(card, {
        rotateX: py * -6,
        rotateY: px * 6,
        transformPerspective: 800,
        duration: 0.4,
        ease: "power2.out",
      });
    });
    card.addEventListener("mouseleave", () => {
      gsap.to(card, { rotateX: 0, rotateY: 0, duration: 0.6, ease: "power3.out" });
    });
  });
});
