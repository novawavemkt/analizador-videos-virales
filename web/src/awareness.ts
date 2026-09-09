export const AWARENESS_STAGES = [
  "inconsciente",
  "consciente_del_problema",
  "consciente_de_la_solucion",
  "consciente_del_producto",
  "muy_consciente",
] as const;

export const AWARENESS_LABELS: Record<string, string> = {
  inconsciente: "Inconsciente",
  consciente_del_problema: "Consciente del problema",
  consciente_de_la_solucion: "Consciente de la solución",
  consciente_del_producto: "Consciente del producto",
  muy_consciente: "Muy consciente",
};

export const AWARENESS_COLORS: Record<string, string> = {
  inconsciente: "#64748b",
  consciente_del_problema: "#f59e0b",
  consciente_de_la_solucion: "#f97316",
  consciente_del_producto: "#0ea5e9",
  muy_consciente: "#10b981",
};
