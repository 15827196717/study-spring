function normalize(value) {
  return value.toLocaleLowerCase("zh-CN").trim();
}

function applySearch(query) {
  const needle = normalize(query);
  let visible = 0;
  document.querySelectorAll("[data-question]").forEach((question) => {
    const matches = !needle || normalize(question.textContent).includes(needle);
    question.hidden = !matches;
    if (matches) visible += 1;
  });
  document.querySelector("[data-search-count]").textContent =
    needle ? `${visible} 个匹配结果` : "";
}

function setActiveHeading(id) {
  document.querySelectorAll("[data-toc] a").forEach((link) => {
    link.toggleAttribute("aria-current", link.hash === `#${id}`);
  });
}

function syncActiveHeading(preferHash = false) {
  const headings = Array.from(document.querySelectorAll("article h2, article h3"));
  if (!headings.length) return;

  let active = headings[0];
  if (preferHash && location.hash) {
    const hashTarget = document.getElementById(location.hash.slice(1));
    if (hashTarget) active = hashTarget;
  } else if (
    scrollY + innerHeight >= document.documentElement.scrollHeight - 1
  ) {
    active = headings[headings.length - 1];
  } else {
    const activationLine = 1;
    for (const heading of headings) {
      if (heading.getBoundingClientRect().top > activationLine) break;
      active = heading;
    }
  }
  setActiveHeading(active.id);
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("spring-notes-theme", theme);
}

function updateProgress() {
  const maximum = document.documentElement.scrollHeight - window.innerHeight;
  const percent = maximum > 0 ? (window.scrollY / maximum) * 100 : 0;
  document.querySelector("[data-progress]").style.width = `${percent}%`;
}

const searchInput = document.querySelector("[data-search-input]");
const themeButton = document.querySelector("[data-theme-toggle]");
const tocButton = document.querySelector("[data-toc-toggle]");
const toc = document.querySelector("[data-toc]");
const backToTop = document.querySelector("[data-back-to-top]");
const savedTheme = localStorage.getItem("spring-notes-theme");
const preferredTheme = matchMedia("(prefers-color-scheme: dark)").matches
  ? "dark"
  : "light";
setTheme(savedTheme || preferredTheme);

searchInput.addEventListener("input", (event) => applySearch(event.target.value));
themeButton.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  setTheme(next);
});
tocButton.addEventListener("click", () => {
  const open = toc.toggleAttribute("data-open");
  tocButton.setAttribute("aria-expanded", String(open));
});
backToTop.addEventListener("click", () => {
  const behavior = matchMedia("(prefers-reduced-motion: reduce)").matches
    ? "auto"
    : "smooth";
  scrollTo({ top: 0, behavior });
});
addEventListener("scroll", () => {
  updateProgress();
  syncActiveHeading();
  backToTop.hidden = scrollY < 600;
}, { passive: true });
addEventListener("hashchange", () => syncActiveHeading(true));

const observer = new IntersectionObserver(() => syncActiveHeading(), {
  rootMargin: "-10% 0px -75% 0px",
});
document.querySelectorAll("article h2, article h3").forEach(
  (heading) => observer.observe(heading)
);
updateProgress();
syncActiveHeading();
