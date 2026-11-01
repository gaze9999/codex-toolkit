/** Own one browser renderer and its listeners; callers explicitly register resources. */
export function createScene(THREE, canvas, { onFrame, onError, maxDpr = 2 } = {}) {
  if (!canvas || typeof window === 'undefined' || typeof ResizeObserver === 'undefined') {
    return { status: 'unavailable', error: new Error('Browser canvas and ResizeObserver required') };
  }
  if (!Number.isFinite(maxDpr) || maxDpr < 1 || maxDpr > 4) {
    throw new RangeError('maxDpr must be between 1 and 4');
  }
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  } catch (error) {
    onError?.(error);
    return { status: 'unavailable', error };
  }
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
  camera.position.z = 5;
  const resources = new Set();
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let disposed = false;
  let frame = 0;
  let lastSize = '';
  const context = { scene, camera, renderer };

  function render() {
    if (disposed || document.hidden) return;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (!width || !height) return;
    const dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
    const size = `${width}:${height}:${dpr}`;
    if (size !== lastSize) {
      renderer.setPixelRatio(dpr);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      lastSize = size;
    }
    renderer.render(scene, camera);
  }

  function animate(time) {
    frame = 0;
    if (disposed || document.hidden || motion.matches) return;
    try {
      onFrame?.(time / 1000, context);
      render();
      frame = requestAnimationFrame(animate);
    } catch (error) {
      dispose();
      onError?.(error);
    }
  }

  function resume() {
    cancelAnimationFrame(frame);
    frame = 0;
    if (disposed) return;
    render();
    if (onFrame && !document.hidden && !motion.matches) frame = requestAnimationFrame(animate);
  }

  function contextLost(event) {
    event.preventDefault();
    dispose();
    onError?.(new Error('WebGL context lost'));
  }

  const observer = new ResizeObserver(resume);
  observer.observe(canvas);
  document.addEventListener('visibilitychange', resume);
  motion.addEventListener('change', resume);
  canvas.addEventListener('webglcontextlost', contextLost);

  function dispose() {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frame);
    observer.disconnect();
    document.removeEventListener('visibilitychange', resume);
    motion.removeEventListener('change', resume);
    canvas.removeEventListener('webglcontextlost', contextLost);
    const failures = [];
    for (const resource of resources) {
      try { resource.dispose(); } catch (error) { failures.push(error); }
    }
    resources.clear();
    scene.clear();
    renderer.dispose();
    if (failures.length) onError?.(new AggregateError(failures, 'Resource cleanup failed'));
  }

  function track(resource) {
    if (disposed || typeof resource?.dispose !== 'function') throw new TypeError('Active scene and disposable resource required');
    resources.add(resource);
    return resource;
  }

  resume();
  return { status: 'ready', ...context, render, dispose, track };
}
