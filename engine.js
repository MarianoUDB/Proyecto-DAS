// El navegador ejecuta el mismo motor Python en un hilo separado de la interfaz.
let engineWorker = null;
let requestId = 0;
const engineRequests = new Map();

function stopBrowserEngine(message) {
    engineWorker?.terminate();
    engineWorker = null;
    for (const pending of engineRequests.values()) {
        clearTimeout(pending.timer);
        pending.reject(new Error(message));
    }
    engineRequests.clear();
}

function runBrowserEngine(method, params) {
    if (!engineWorker) {
        engineWorker = new Worker(new URL("engine-worker.js?v=3", document.baseURI), { type: "module" });
        engineWorker.onmessage = ({ data }) => {
            if (data.progress) {
                document.getElementById("engine-status").textContent = data.progress;
                return;
            }
            const pending = engineRequests.get(data.id);
            if (!pending) return;
            clearTimeout(pending.timer);
            engineRequests.delete(data.id);
            if (data.error) pending.reject(new Error(data.error));
            else pending.resolve(data.result);
        };
        engineWorker.onerror = () => stopBrowserEngine("No se pudo iniciar el motor. Comprueba la conexión y pulsa Simular vuelo para reintentar.");
    }
    return new Promise((resolve, reject) => {
        const id = ++requestId;
        const timer = setTimeout(() => stopBrowserEngine("El motor tardó demasiado. Comprueba la conexión y vuelve a intentar."), 180000);
        engineRequests.set(id, { resolve, reject, timer });
        engineWorker.postMessage({ id, method, params });
    });
}
