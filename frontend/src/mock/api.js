// Mock API delay helper
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const STEPS = [
  'Searching sources',
  'Extracting factual claims',
  'Verifying evidence',
  'Scoring confidence',
  'Synthesizing answer'
];

// In-memory store
let queries = {};

export const submitQuery = async (question) => {
  await delay(800);
  const id = 'query_' + Date.now();
  queries[id] = {
    id,
    question,
    status: 'IN_PROGRESS',
    stepIndex: 0,
    startTime: Date.now(),
    result: null
  };
  
  // Start the "backend" process
  simulateBackendProcess(id);
  
  return { query_id: id };
};

const simulateBackendProcess = async (id) => {
  const q = queries[id];
  if (!q) return;

  // Step 1: Searching
  await delay(1500);
  q.stepIndex = 1; // Extracting
  
  // Step 2: Extracting
  await delay(1500);
  q.stepIndex = 2; // Verifying
  
  // Step 3: Verifying (Longer)
  await delay(2000);
  q.stepIndex = 3; // Scoring
  
  // Step 4: Scoring
  await delay(1000);
  q.stepIndex = 4; // Synthesizing
  
  // Step 5: Synthesizing
  await delay(1500);
  
  // Complete
  q.status = 'COMPLETED';
  q.result = generateMockResult(q.question);
};

export const pollStatus = async (id) => {
  await delay(200);
  const q = queries[id];
  if (!q) throw new Error("Query not found");
  
  return {
    query_id: id,
    status: q.status,
    pipeline_step: STEPS[q.stepIndex],
    current_step_index: q.stepIndex,
    is_complete: q.status === 'COMPLETED'
  };
};

export const fetchResult = async (id) => {
  await delay(500);
  const q = queries[id];
  if (!q || !q.result) throw new Error("Result not ready");
  return q.result;
};

const generateMockResult = (question) => {
  const isSilly = question.toLowerCase().includes('silly') || question.toLowerCase().includes('clay');
  
  return {
    answer: `Based on the analysis of multiple verified sources, the answer to "${question}" is complex but affirmative. The data suggests a strong correlation between claymation aesthetics and user engagement, primarily due to the "nostalgia factor" and "tactile novelty". Sources indicate that users spend 40% more time on interfaces that appear "hand-crafted".`,
    
    confidence_level: 'HIGH', // HIGH, MEDIUM, LOW
    confidence_reason: '3 out of 4 major sources corroborate the primary claim. No significant conflicts detected.',
    
    evidence: [
      {
        claim: 'Claymation interfaces increase dwell time by 40%.',
        status: 'VERIFIED',
        source: 'https://example.com/ux-study-2025'
      },
      {
        claim: 'Users perceive "hand-sculpted" elements as more trustworthy.',
        status: 'VERIFIED',
        source: 'https://journal.design/tactile-web'
      },
      {
        claim: 'Plasticine textures reduce bounce rate.',
        status: 'UNVERIFIED', // or CONFLICT
        source: 'https://measure.io/report'
      }
    ],
    
    planner_trace: [
      { attempt: 1, strategy: 'Keyword Search', documents: 15, decision: 'ACCEPT' },
      { attempt: 2, strategy: 'Deep Deep verification', documents: 5, decision: 'STOP' }
    ]
  };
};
