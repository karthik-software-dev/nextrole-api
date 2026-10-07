// Native Web Audio API Sound Synthesizer
// Louder, studio-compressed audio optimized for laptop and desktop speakers
// Requires zero external sound assets, 100% native, instant playback

let sharedAudioCtx: AudioContext | null = null;

const getAudioContext = (): AudioContext | null => {
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return null;
    if (!sharedAudioCtx || sharedAudioCtx.state === 'closed') {
      sharedAudioCtx = new AudioContextClass();
    }
    if (sharedAudioCtx.state === 'suspended') {
      sharedAudioCtx.resume().catch(() => {});
    }
    return sharedAudioCtx;
  } catch {
    return null;
  }
};

// Master dynamics compressor to ensure punchy, loud volume without clipping/distortion
const createMasterOutput = (ctx: AudioContext) => {
  const compressor = ctx.createDynamicsCompressor();
  compressor.threshold.setValueAtTime(-14, ctx.currentTime);
  compressor.knee.setValueAtTime(8, ctx.currentTime);
  compressor.ratio.setValueAtTime(3.5, ctx.currentTime);
  compressor.attack.setValueAtTime(0.002, ctx.currentTime);
  compressor.release.setValueAtTime(0.12, ctx.currentTime);
  compressor.connect(ctx.destination);
  return compressor;
};

// 1. Success Chime: 3-tone bright chord (C5 -> E5 -> G5)
export const playDiscoverySuccessSound = () => {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const master = createMasterOutput(ctx);

    // Note 1: C5 (523.25 Hz)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(523.25, now);
    gain1.gain.setValueAtTime(0.38, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    osc1.connect(gain1);
    gain1.connect(master);
    osc1.start(now);
    osc1.stop(now + 0.3);

    // Note 2: E5 (659.25 Hz)
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(659.25, now + 0.09);
    gain2.gain.setValueAtTime(0.42, now + 0.09);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
    osc2.connect(gain2);
    gain2.connect(master);
    osc2.start(now + 0.09);
    osc2.stop(now + 0.4);

    // Note 3: G5 (783.99 Hz) with overtone
    const osc3 = ctx.createOscillator();
    const gain3 = ctx.createGain();
    osc3.type = 'triangle';
    osc3.frequency.setValueAtTime(783.99, now + 0.18);
    gain3.gain.setValueAtTime(0.48, now + 0.18);
    gain3.gain.exponentialRampToValueAtTime(0.001, now + 0.65);
    osc3.connect(gain3);
    gain3.connect(master);
    osc3.start(now + 0.18);
    osc3.stop(now + 0.65);
  } catch (err) {
    console.debug('Audio playback skipped:', err);
  }
};

// 2. Resume Tone: Bright, energetic ascending chime (587Hz -> 880Hz)
export const playDiscoveryResumeSound = () => {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const master = createMasterOutput(ctx);

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(587.33, now);
    osc.frequency.exponentialRampToValueAtTime(880.0, now + 0.18);

    gain.gain.setValueAtTime(0.46, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

    osc.connect(gain);
    gain.connect(master);
    osc.start(now);
    osc.stop(now + 0.3);
  } catch (err) {
    console.debug('Resume sound skipped:', err);
  }
};

// 3. Pause Tone: Distinct two-tone hold cue (720Hz -> 540Hz)
export const playDiscoveryPauseSound = () => {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const master = createMasterOutput(ctx);

    // Tone 1
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(720, now);
    gain1.gain.setValueAtTime(0.44, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
    osc1.connect(gain1);
    gain1.connect(master);
    osc1.start(now);
    osc1.stop(now + 0.14);

    // Tone 2
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(540, now + 0.1);
    gain2.gain.setValueAtTime(0.40, now + 0.1);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
    osc2.connect(gain2);
    gain2.connect(master);
    osc2.start(now + 0.1);
    osc2.stop(now + 0.28);
  } catch (err) {
    console.debug('Pause sound skipped:', err);
  }
};

// 4. Stop Tone: Low solid descending confirmation tone (480Hz -> 320Hz)
export const playDiscoveryStopSound = () => {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const master = createMasterOutput(ctx);

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(480, now);
    osc.frequency.exponentialRampToValueAtTime(320, now + 0.2);

    gain.gain.setValueAtTime(0.44, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.32);

    osc.connect(gain);
    gain.connect(master);
    osc.start(now);
    osc.stop(now + 0.32);
  } catch (err) {
    console.debug('Stop sound skipped:', err);
  }
};

// 5. Start / Launch Tone: Energetic rising two-pulse chord (440Hz -> 659Hz -> 880Hz)
export const playDiscoveryStartSound = () => {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const master = createMasterOutput(ctx);

    // Pulse 1: Warm punchy intro tone (440Hz -> 659.25Hz)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(440, now);
    osc1.frequency.exponentialRampToValueAtTime(659.25, now + 0.12);
    gain1.gain.setValueAtTime(0.42, now);
    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.14);
    osc1.connect(gain1);
    gain1.connect(master);
    osc1.start(now);
    osc1.stop(now + 0.14);

    // Pulse 2: Bright ascending shimmer (880Hz -> 1046.5Hz)
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'triangle';
    osc2.frequency.setValueAtTime(880, now + 0.08);
    osc2.frequency.exponentialRampToValueAtTime(1046.5, now + 0.28);
    gain2.gain.setValueAtTime(0.46, now + 0.08);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
    osc2.connect(gain2);
    gain2.connect(master);
    osc2.start(now + 0.08);
    osc2.stop(now + 0.45);
  } catch (err) {
    console.debug('Start sound skipped:', err);
  }
};

// 6. Job Apply / Dispatched Sound: Uplifting send chime (C5 523Hz -> G5 784Hz -> C6 1046Hz)
export const playJobApplySound = () => {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const master = createMasterOutput(ctx);

    // Tone 1: Swift ascending whoosh glide (523Hz -> 784Hz)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(523.25, now);
    osc1.frequency.exponentialRampToValueAtTime(783.99, now + 0.1);
    gain1.gain.setValueAtTime(0.40, now);
    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.12);
    osc1.connect(gain1);
    gain1.connect(master);
    osc1.start(now);
    osc1.stop(now + 0.12);

    // Tone 2: Crystalline resolution chime (1046.5Hz)
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'triangle';
    osc2.frequency.setValueAtTime(1046.5, now + 0.08);
    gain2.gain.setValueAtTime(0.44, now + 0.08);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.38);
    osc2.connect(gain2);
    gain2.connect(master);
    osc2.start(now + 0.08);
    osc2.stop(now + 0.38);
  } catch (err) {
    console.debug('Apply sound skipped:', err);
  }
};

// 7. Mechanical Toggle Switch Sound: Louder, crisp tactile dual-transient click (~70ms)
export const playToggleSwitchSound = (mode?: 'cache' | 'live') => {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const master = createMasterOutput(ctx);

    // Transient 1: Sharp contact snap (triangle wave with upper harmonics for laptop speakers)
    const snapOsc = ctx.createOscillator();
    const snapGain = ctx.createGain();
    snapOsc.type = 'triangle';

    if (mode === 'live') {
      // Ascending crisp snap for real-time live mode
      snapOsc.frequency.setValueAtTime(1150, now);
      snapOsc.frequency.exponentialRampToValueAtTime(1750, now + 0.028);
    } else if (mode === 'cache') {
      // Solid downward latch for test cache snapshot
      snapOsc.frequency.setValueAtTime(1650, now);
      snapOsc.frequency.exponentialRampToValueAtTime(920, now + 0.028);
    } else {
      // General crisp mechanical click
      snapOsc.frequency.setValueAtTime(1500, now);
      snapOsc.frequency.exponentialRampToValueAtTime(980, now + 0.028);
    }

    snapGain.gain.setValueAtTime(0.58, now);
    snapGain.gain.exponentialRampToValueAtTime(0.001, now + 0.045);
    snapOsc.connect(snapGain);
    snapGain.connect(master);
    snapOsc.start(now);
    snapOsc.stop(now + 0.045);

    // Transient 2: Warm resonant body undertone giving physical weight to the switch
    const bodyOsc = ctx.createOscillator();
    const bodyGain = ctx.createGain();
    bodyOsc.type = 'sine';
    const bodyFreq = mode === 'live' ? 520 : 420;
    bodyOsc.frequency.setValueAtTime(bodyFreq, now + 0.006);
    bodyOsc.frequency.exponentialRampToValueAtTime(bodyFreq * 0.7, now + 0.065);

    bodyGain.gain.setValueAtTime(0.48, now + 0.006);
    bodyGain.gain.exponentialRampToValueAtTime(0.001, now + 0.07);
    bodyOsc.connect(bodyGain);
    bodyGain.connect(master);
    bodyOsc.start(now + 0.006);
    bodyOsc.stop(now + 0.07);
  } catch (err) {
    console.debug('Toggle switch sound skipped:', err);
  }
};

