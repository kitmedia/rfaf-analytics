/**
 * Parsea el markdown generado por el prompt P3 (FORMACION_ENTRENAMIENTO.md)
 * en datos estructurados para renderizar ExerciseCards.
 */

export interface ParsedExercise {
  name: string;
  objetivo: string;
  organizacion: string;
  descripcion: string;
  variantes: string;
  duracion: string;
}

export interface ParsedTrainingPlan {
  analisisDidactico: string;
  ejercicios: ParsedExercise[];
  conceptosTacticos: string;
  planSemanal: string;
  recursos: string;
}

function extractField(text: string, fieldName: string): string {
  const regex = new RegExp(
    `- \\*\\*${fieldName}:\\*\\*\\s*([\\s\\S]*?)(?=\\n- \\*\\*|\\n#{1,4} |$)`,
    "i",
  );
  const match = text.match(regex);
  return match ? match[1].trim() : "";
}

function parseSections(markdown: string): Record<string, string> {
  const sections: Record<string, string> = {};
  // Split by ### headers (level 3)
  const parts = markdown.split(/^### /m);

  for (const part of parts) {
    if (!part.trim()) continue;
    const firstNewline = part.indexOf("\n");
    if (firstNewline === -1) continue;
    const header = part.substring(0, firstNewline).trim();
    const content = part.substring(firstNewline + 1).trim();

    if (header.match(/1\.\s*An[aá]lisis Did[aá]ctico/i)) {
      sections.analisis = content;
    } else if (header.match(/2\.\s*Ejercicios/i)) {
      sections.ejercicios = content;
    } else if (header.match(/3\.\s*Conceptos T[aá]cticos/i)) {
      sections.conceptos = content;
    } else if (header.match(/4\.\s*Plan Semanal/i)) {
      sections.plan = content;
    } else if (header.match(/5\.\s*Recursos/i)) {
      sections.recursos = content;
    }
  }

  return sections;
}

function parseExercises(exercisesMarkdown: string): ParsedExercise[] {
  const exercises: ParsedExercise[] = [];
  // Split by #### Ejercicio headers
  const parts = exercisesMarkdown.split(/^#### Ejercicio \d+:\s*/m);

  for (const part of parts) {
    if (!part.trim()) continue;

    const firstNewline = part.indexOf("\n");
    if (firstNewline === -1) continue;

    const name = part.substring(0, firstNewline).trim().replace(/\*+/g, "");
    const body = part.substring(firstNewline + 1);

    const exercise: ParsedExercise = {
      name,
      objetivo: extractField(body, "Objetivo t[aá]ctico"),
      organizacion: extractField(body, "Organizaci[oó]n"),
      descripcion: extractField(body, "Descripci[oó]n"),
      variantes: extractField(body, "Variantes"),
      duracion: extractField(body, "Duraci[oó]n"),
    };

    // Only include if we got at least the name and one field
    if (name && (exercise.objetivo || exercise.descripcion)) {
      exercises.push(exercise);
    }
  }

  return exercises;
}

/**
 * Parsea el markdown del plan de entrenamiento P3.
 * Retorna null si el parseo falla completamente.
 * Si el parseo es parcial (algunos ejercicios), retorna lo que pudo extraer.
 */
export function parseTrainingPlan(
  markdown: string,
): ParsedTrainingPlan | null {
  try {
    const sections = parseSections(markdown);

    // If we can't find the exercises section, fail
    if (!sections.ejercicios) return null;

    const ejercicios = parseExercises(sections.ejercicios);

    // If no exercises parsed, fail
    if (ejercicios.length === 0) return null;

    return {
      analisisDidactico: sections.analisis || "",
      ejercicios,
      conceptosTacticos: sections.conceptos || "",
      planSemanal: sections.plan || "",
      recursos: sections.recursos || "",
    };
  } catch {
    return null;
  }
}
