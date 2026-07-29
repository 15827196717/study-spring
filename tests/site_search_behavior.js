const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function eventTarget(extra = {}) {
  const listeners = new Map();
  return {
    ...extra,
    addEventListener(type, listener) {
      listeners.set(type, listener);
    },
    dispatch(type, event) {
      listeners.get(type)(event);
    },
  };
}

function question(text, onHidden) {
  const element = { textContent: text, _hidden: false };
  Object.defineProperty(element, "hidden", {
    get() {
      return this._hidden;
    },
    set(value) {
      this._hidden = value;
      onHidden(value);
    },
  });
  return element;
}

function heading(id, top, owner = null) {
  return {
    id,
    getBoundingClientRect() {
      return { top };
    },
    closest(selector) {
      assert.equal(selector, "[hidden]");
      return owner && owner.hidden ? owner : null;
    },
  };
}

function tocLink(hash) {
  return {
    hash,
    current: false,
    toggleAttribute(name, enabled) {
      assert.equal(name, "aria-current");
      this.current = enabled;
    },
  };
}

const root = { dataset: {}, scrollHeight: 2000 };
const firstQuestion = question("cycle dependencies", () => {});
const secondQuestion = question("other answer", (hidden) => {
  root.scrollHeight = hidden ? 1500 : 2000;
});
const headings = [
  heading("01-one", -100),
  heading("q-1-1", -50, firstQuestion),
  heading("q-2-2", 0, secondQuestion),
];
const links = headings.map((item) => tocLink(`#${item.id}`));
const searchInput = eventTarget();
const searchCount = { textContent: "" };
const themeButton = eventTarget();
const tocButton = eventTarget({
  setAttribute() {},
});
const toc = {
  toggleAttribute() {
    return true;
  },
};
const backToTop = eventTarget({ hidden: true });
const progress = { style: { width: "" } };
const globalListeners = new Map();

const document = {
  documentElement: root,
  querySelectorAll(selector) {
    if (selector === "[data-question]") return [firstQuestion, secondQuestion];
    if (selector === "[data-toc] a") return links;
    if (selector === "article h2, article h3") return headings;
    throw new Error(`unexpected selector: ${selector}`);
  },
  querySelector(selector) {
    return {
      "[data-search-input]": searchInput,
      "[data-search-count]": searchCount,
      "[data-theme-toggle]": themeButton,
      "[data-toc-toggle]": tocButton,
      "[data-toc]": toc,
      "[data-back-to-top]": backToTop,
      "[data-progress]": progress,
    }[selector];
  },
  getElementById(id) {
    return headings.find((item) => item.id === id);
  },
};

const context = {
  console,
  document,
  location: { hash: "" },
  localStorage: {
    getItem() {
      return null;
    },
    setItem() {},
  },
  matchMedia() {
    return { matches: false };
  },
  scrollY: 1000,
  innerHeight: 500,
  scrollTo() {},
  addEventListener(type, listener) {
    globalListeners.set(type, listener);
  },
  IntersectionObserver: class {
    constructor(callback) {
      this.callback = callback;
    }
    observe() {}
  },
};
context.window = context;

const source = fs.readFileSync(path.join(__dirname, "..", "site", "app.js"), "utf8");
vm.runInNewContext(source, context, { filename: "site/app.js" });

assert.equal(
  links.find((link) => link.current).hash,
  "#q-2-2",
  "precondition: the lower visible heading starts active",
);

searchInput.dispatch("input", { target: { value: "cycle" } });
assert.equal(secondQuestion.hidden, true);
assert.equal(
  links.find((link) => link.current).hash,
  "#q-1-1",
  "search must not leave aria-current on a heading inside hidden content",
);
assert.equal(progress.style.width, "100%", "search must immediately update progress");

searchInput.dispatch("input", { target: { value: "" } });
assert.equal(secondQuestion.hidden, false);
assert.equal(
  links.find((link) => link.current).hash,
  "#q-2-2",
  "clearing search must restore active-heading selection",
);
assert.equal(
  progress.style.width,
  "66.66666666666666%",
  "clearing search must restore progress for the full document",
);
