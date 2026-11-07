const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function dashboard() {
    const elements = new Map();
    const context = vm.createContext({
        document: {
            getElementById(id) {
                if (!elements.has(id)) elements.set(id, {});
                return elements.get(id);
            }
        },
        window: { addEventListener() {} },
        fetch: async () => ({ ok: false }),
        performance: { now: () => 100 },
        requestAnimationFrame(callback) { context.frame = callback; return 1; },
        cancelAnimationFrame() {}
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, "../web/app.js"), "utf8"), context);
    return { context, elements };
}

test("la primera animación no usa un índice negativo y respeta el paso de telemetría", () => {
    const { context } = dashboard();
    vm.runInContext(`
        state.simData = { data: { time: Array.from({length: 10}, (_, i) => i * 0.04) } };
        renderCurrentFrame = () => {};
        startAnimationLoop();
    `, context);
    context.frame(99);
    assert.equal(vm.runInContext("state.currentIndex", context), 0);
    context.frame(199);
    assert.equal(vm.runInContext("state.currentIndex", context), 2.5);
    context.frame(1199);
    assert.equal(vm.runInContext("state.currentIndex", context), 9);
    assert.equal(vm.runInContext("state.isPlaying", context), false);
});

test("una nueva corrida limpia las compuertas del vuelo anterior", () => {
    const { context, elements } = dashboard();
    elements.get("gate-imc-status").textContent = "ESTABILIZADA";
    elements.get("touchdown-status").textContent = "TOUCHDOWN EXITOSO";
    vm.runInContext("updateStaticSummaries({ events: [] })", context);
    assert.equal(elements.get("gate-imc-status").textContent, "NO ALCANZADA");
    assert.equal(elements.get("touchdown-status").textContent, "NO ALCANZADA");
});
