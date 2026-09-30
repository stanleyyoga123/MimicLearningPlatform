export type SkillTopic = 'API design' | 'Data modeling' | 'Testing' | 'Reliability';

export type MentorLearner = {
  name: string;
  initials: string;
  level: string;
  status: 'Needs a nudge' | 'On track' | 'Ready for a stretch';
  completed: number;
  inProgress: boolean;
  skills: Record<SkillTopic, number>;
  suggestedTask: string;
  taskReason: string;
  taskDuration: string;
  checkIn?: string;
};

export const skillTopics: SkillTopic[] = ['API design', 'Data modeling', 'Testing', 'Reliability'];

export const demoCohort: MentorLearner[] = [
  {
    name: 'Stanley Yoga', initials: 'SY', level: 'Developing practitioner',
    status: 'Needs a nudge', completed: 6, inProgress: true,
    skills: { 'API design': 82, 'Data modeling': 73, Testing: 64, Reliability: 48 },
    suggestedTask: 'Make webhook deliveries idempotent',
    taskReason: 'Practice safe retries before they become duplicate orders.',
    taskDuration: '45 min',
    checkIn: 'Ask how Stanley is identifying duplicate events before changing the handler.',
  },
  {
    name: 'Aisha Rahman', initials: 'AR', level: 'Developing practitioner',
    status: 'On track', completed: 5, inProgress: true,
    skills: { 'API design': 74, 'Data modeling': 69, Testing: 52, Reliability: 71 },
    suggestedTask: 'Add regression coverage for order states',
    taskReason: 'Turn an edge case into a test that protects the fix.',
    taskDuration: '40 min',
  },
  {
    name: 'Leo Chen', initials: 'LC', level: 'Foundations',
    status: 'Needs a nudge', completed: 3, inProgress: false,
    skills: { 'API design': 43, 'Data modeling': 58, Testing: 61, Reliability: 55 },
    suggestedTask: 'Define a clear validation response',
    taskReason: 'Strengthen endpoint contracts and error handling.',
    taskDuration: '35 min',
    checkIn: 'Review the request and response contract together before another implementation.',
  },
  {
    name: 'Priya Nair', initials: 'PN', level: 'Confident builder',
    status: 'Ready for a stretch', completed: 8, inProgress: false,
    skills: { 'API design': 87, 'Data modeling': 76, Testing: 83, Reliability: 67 },
    suggestedTask: 'Handle an out-of-order event',
    taskReason: 'Build on strong test habits with a reliability edge case.',
    taskDuration: '55 min',
  },
  {
    name: 'Mateo Silva', initials: 'MS', level: 'Developing practitioner',
    status: 'On track', completed: 4, inProgress: true,
    skills: { 'API design': 71, 'Data modeling': 49, Testing: 66, Reliability: 62 },
    suggestedTask: 'Protect a database constraint',
    taskReason: 'Explore how persistence rules support API behavior.',
    taskDuration: '45 min',
  },
];

export function weakestTopic(learner: MentorLearner): SkillTopic {
  return skillTopics.reduce((weakest, topic) =>
    learner.skills[topic] < learner.skills[weakest] ? topic : weakest,
  );
}
