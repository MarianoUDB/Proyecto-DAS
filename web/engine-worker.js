import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";

let engineReady;

async function loadEngine() {
    self.postMessage({ progress: "Vista previa precalculada · Cargando motor Python. La primera carga puede tardar; no necesitas instalar nada." });
    const pyodide = await loadPyodide();
    self.postMessage({ progress: "Cargando cálculo numérico…" });
    await pyodide.loadPackage("numpy");
    const response = await fetch(new URL("aero_gnc.zip?v=3", import.meta.url));
    if (!response.ok) throw new Error("No se encontró el motor de simulación.");
    pyodide.unpackArchive(await response.arrayBuffer(), "zip");
    pyodide.runPython("import json\nfrom aero_gnc.visualization.dashboard_data import simulate_dashboard, validate_dashboard");
    return pyodide;
}

self.onmessage = async ({ data: { id, method, params } }) => {
    try {
        if (!engineReady) engineReady = loadEngine().catch((error) => { engineReady = null; throw error; });
        const pyodide = await engineReady;
        pyodide.globals.set("request_json", JSON.stringify(params));
        let expression;
        if (method === "simulate") {
            self.postMessage({ progress: "Calculando vuelo con las condiciones seleccionadas…" });
            expression = "simulate_dashboard(json.loads(request_json))";
        } else if (method === "validation") {
            expression = "validate_dashboard(json.loads(request_json)['aircraft_id'])";
        } else {
            throw new Error("Operación desconocida.");
        }
        const result = JSON.parse(pyodide.runPython(`json.dumps(${expression}, allow_nan=False)`));
        self.postMessage({ id, result });
    } catch (error) {
        self.postMessage({ id, error: error.message });
    }
};
