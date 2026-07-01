/**
 * Single source of truth for the IEEE-LOM controlled vocabularies used by the
 * authoring UI (contribution wizard, LOM editor) and the /learn filters. These
 * MUST stay in lockstep with the backend model choices in
 * backend/apps/education/models.py — when a choice is added there, add it here
 * and the option shows up everywhere at once.
 */

export const LOM_RESOURCE_TYPES = [
  'narrative_text', 'image', 'audio', 'video', 'document', 'diagram', 'figure',
  'graph', 'slide', 'table', 'exercise', 'simulation', 'questionnaire', 'exam',
  'experiment', 'problem_statement', 'self_assessment', 'lecture',
] as const;

export const LOM_DIFFICULTIES = [
  'very_easy', 'easy', 'medium', 'difficult', 'very_difficult',
] as const;

export const LOM_CONTEXTS = ['school', 'higher_education', 'training', 'other'] as const;

export const LOM_INTERACTIVITY_TYPES = ['active', 'expositive', 'mixed'] as const;

export const LOM_INTERACTIVITY_LEVELS = [
  'very_low', 'low', 'medium', 'high', 'very_high',
] as const;

export const LOM_END_USER_ROLES = ['learner', 'teacher', 'author', 'manager'] as const;

export const LOM_PEDAGOGICAL_APPROACHES = [
  'expository', 'inquiry', 'constructivist', 'project_based', 'collaborative', 'gamified',
] as const;

export const LOM_LIFECYCLE_STATUSES = ['draft', 'final', 'revised', 'unavailable'] as const;

export const LOM_CLASSIFICATION_PURPOSES = [
  'discipline', 'idea', 'prerequisite', 'educational_objective', 'accessibility_restrictions',
  'educational_level', 'skill_level', 'security_level', 'competency',
] as const;
