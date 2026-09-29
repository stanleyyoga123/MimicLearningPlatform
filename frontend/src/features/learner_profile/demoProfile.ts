export type ProfileMetric = {
  label: string;
  value: string;
  detail: string;
};

export type ProfileSkill = {
  name: string;
  level: number;
  note: string;
};

export type ProfileActivity = {
  day: string;
  minutes: number;
};

export const demoProfile = {
  name: 'Jordan Lee',
  initials: 'JL',
  track: 'Backend engineering',
  level: 'Developing practitioner',
  metrics: [
    { label: 'Available assignments', value: '08', detail: 'In this sample catalog' },
    { label: 'Completed', value: '06', detail: 'Practice assignments' },
    { label: 'In progress', value: '01', detail: 'Current learning task' },
    { label: 'Learning time', value: '24h', detail: 'Across this sample profile' },
  ] satisfies ProfileMetric[],
  skills: [
    { name: 'API design', level: 82, note: 'Strong' },
    { name: 'Data modeling', level: 73, note: 'On track' },
    { name: 'Testing & debugging', level: 64, note: 'Building' },
    { name: 'Reliability', level: 48, note: 'Focus area' },
  ] satisfies ProfileSkill[],
  activity: [
    { day: 'Mon', minutes: 35 },
    { day: 'Tue', minutes: 70 },
    { day: 'Wed', minutes: 50 },
    { day: 'Thu', minutes: 90 },
    { day: 'Fri', minutes: 60 },
    { day: 'Sat', minutes: 20 },
    { day: 'Sun', minutes: 0 },
  ] satisfies ProfileActivity[],
  strengths: [
    { title: 'Clear API contracts', detail: 'Consistently defines request and response behavior before implementation.' },
    { title: 'Data flow reasoning', detail: 'Traces changes through endpoints, persistence, and observable results.' },
  ],
  growthAreas: [
    { title: 'Retry-safe operations', detail: 'Practice handling repeated requests without duplicating side effects.' },
    { title: 'Regression coverage', detail: 'Add a focused failing test before fixing an edge case.' },
  ],
  recommendations: [
    { category: 'RELIABILITY', title: 'Make webhook deliveries idempotent', detail: 'Practice safe retries and duplicate event handling.', duration: '45 MIN' },
    { category: 'TESTING', title: 'Protect an order state transition', detail: 'Turn a bug report into a durable regression test.', duration: '40 MIN' },
  ],
  milestones: [
    { title: 'First code review approved', detail: 'Order validation exercise', date: 'WEEK 3' },
    { title: 'Completed API design path', detail: 'Three related assignments', date: 'WEEK 2' },
    { title: 'Started backend track', detail: 'Practice profile created', date: 'WEEK 1' },
  ],
} as const;
