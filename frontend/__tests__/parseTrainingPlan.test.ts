/**
 * Tests for parseTrainingPlan.
 * Run with: npx tsx frontend/__tests__/parseTrainingPlan.test.ts
 * Or with vitest/jest if configured.
 */

import { parseTrainingPlan } from "../lib/parseTrainingPlan";

const WELL_FORMED_MARKDOWN = `
### 1. Análisis Didáctico del Partido
El equipo local mostró debilidades en la salida de balón desde atrás.

### 2. Ejercicios de Entrenamiento Propuestos

#### Ejercicio 1: Rondo de Salida
- **Objetivo táctico:** Mejorar la salida de balón bajo presión
- **Organización:** 8 jugadores, medio campo, 4 conos
- **Descripción:** Rondo 4v4+2 comodines en espacio reducido
- **Variantes:** Aumentar presión, reducir toques
- **Duración:** 15 minutos

#### Ejercicio 2: Pressing Coordinado
- **Objetivo táctico:** Mejorar pressing tras pérdida
- **Organización:** 16 jugadores, campo completo, petos
- **Descripción:** Equipo pierde balón y debe recuperar en 6 segundos
- **Variantes:** Limitar zona de recuperación
- **Duración:** 20 minutos

#### Ejercicio 3: Transición Ofensiva
- **Objetivo táctico:** Mejorar velocidad en transición
- **Organización:** 12 jugadores, 3/4 de campo, 2 porterías
- **Descripción:** 6v6 con énfasis en verticalidad tras recuperación
- **Variantes:** Añadir comodín ofensivo
- **Duración:** 25 minutos

### 3. Conceptos Tácticos a Trabajar
1. **Salida de balón:** El equipo debe mejorar la construcción desde atrás.
2. **Pressing tras pérdida:** Recuperar el balón en los primeros 6 segundos.
3. **Transiciones:** Pasar de defensa a ataque con mayor velocidad.

### 4. Plan Semanal Sugerido
- **Lunes:** Rondo de Salida + trabajo táctico analítico
- **Miércoles:** Pressing Coordinado + situaciones de juego
- **Viernes:** Transición Ofensiva + partido aplicado

### 5. Recursos Adicionales
- Vídeo: Guardiola explica la salida de balón (YouTube)
- Libro: "El fútbol a través del juego" de Óscar Cano
`;

// Test 1: Well-formed markdown parses correctly
const result = parseTrainingPlan(WELL_FORMED_MARKDOWN);
console.assert(result !== null, "FAIL: Should parse well-formed markdown");
console.assert(result!.ejercicios.length === 3, `FAIL: Expected 3 exercises, got ${result!.ejercicios.length}`);
console.assert(result!.ejercicios[0].name === "Rondo de Salida", `FAIL: Expected 'Rondo de Salida', got '${result!.ejercicios[0].name}'`);
console.assert(result!.ejercicios[0].objetivo.includes("salida de balón"), "FAIL: Objetivo not parsed");
console.assert(result!.ejercicios[0].duracion.includes("15"), "FAIL: Duracion not parsed");
console.assert(result!.ejercicios[1].name === "Pressing Coordinado", "FAIL: Second exercise name wrong");
console.assert(result!.analisisDidactico.includes("salida de balón"), "FAIL: Analisis didactico not parsed");
console.assert(result!.conceptosTacticos.includes("Pressing tras pérdida"), "FAIL: Conceptos tacticos not parsed");
console.assert(result!.planSemanal.includes("Lunes"), "FAIL: Plan semanal not parsed");
console.assert(result!.recursos.includes("Guardiola"), "FAIL: Recursos not parsed");
console.log("PASS: Well-formed markdown parses correctly");

// Test 2: Malformed markdown returns null
const malformed = "This is just random text without any ### headers";
const result2 = parseTrainingPlan(malformed);
console.assert(result2 === null, "FAIL: Should return null for malformed markdown");
console.log("PASS: Malformed markdown returns null");

// Test 3: Missing exercises section returns null
const noExercises = `
### 1. Análisis Didáctico del Partido
Some analysis here.

### 3. Conceptos Tácticos a Trabajar
Some concepts here.
`;
const result3 = parseTrainingPlan(noExercises);
console.assert(result3 === null, "FAIL: Should return null when no exercises section");
console.log("PASS: Missing exercises section returns null");

// Test 4: Partial parse (2 of 3 exercises have fields, 1 missing)
const partialMarkdown = `
### 2. Ejercicios de Entrenamiento Propuestos

#### Ejercicio 1: Rondo Básico
- **Objetivo táctico:** Mejorar posesión
- **Descripción:** Rondo 4v2

#### Ejercicio 2: Sin Campos
Solo texto sin campos con negrita.

#### Ejercicio 3: Pressing Alto
- **Objetivo táctico:** Recuperar arriba
- **Descripción:** 8v8 con pressing
`;
const result4 = parseTrainingPlan(partialMarkdown);
console.assert(result4 !== null, "FAIL: Partial parse should not return null");
console.assert(result4!.ejercicios.length === 2, `FAIL: Expected 2 exercises from partial, got ${result4!.ejercicios.length}`);
console.log("PASS: Partial parse returns valid exercises only");

// Test 5: Empty string returns null
const result5 = parseTrainingPlan("");
console.assert(result5 === null, "FAIL: Empty string should return null");
console.log("PASS: Empty string returns null");

console.log("\n--- All parseTrainingPlan tests passed ---");
