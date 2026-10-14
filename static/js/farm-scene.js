const THREE_MODULE = 'https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js';
const scenes = document.querySelectorAll('[data-farm-scene]');

function setFallback(element) {
  element.dataset.sceneState = 'fallback';
}

function terrainGeometry(THREE, width, depth, segmentsX = 32, segmentsZ = 24) {
  const geometry = new THREE.PlaneGeometry(width, depth, segmentsX, segmentsZ);
  const positions = geometry.attributes.position;
  for (let index = 0; index < positions.count; index += 1) {
    const x = positions.getX(index);
    const z = positions.getY(index);
    const hill = Math.sin(x * 0.15 + z * 0.08) * 0.32 + Math.cos(z * 0.19) * 0.18;
    positions.setZ(index, hill);
  }
  positions.needsUpdate = true;
  geometry.computeVertexNormals();
  geometry.rotateX(-Math.PI / 2);
  return geometry;
}

function addLighting(THREE, scene) {
  scene.add(new THREE.HemisphereLight(0xdde9d1, 0x314a37, 2.1));
  const sunLight = new THREE.DirectionalLight(0xffe1ad, 2.8);
  sunLight.position.set(-8, 14, 7);
  sunLight.castShadow = false;
  scene.add(sunLight);
  const fill = new THREE.DirectionalLight(0xa8c9b0, 1.1);
  fill.position.set(9, 5, -8);
  scene.add(fill);
}

function makeCloud(THREE, scene, x, y, z, scale) {
  const cloud = new THREE.Group();
  const material = new THREE.MeshStandardMaterial({ color: 0xf1eee0, roughness: 1, transparent: true, opacity: 0.7 });
  [[0, 0, 0, 1.05], [0.65, 0.12, 0, 0.76], [-0.63, 0.08, 0, 0.72]].forEach(([cx, cy, cz, size]) => {
    const puff = new THREE.Mesh(new THREE.SphereGeometry(size, 8, 6), material);
    puff.position.set(cx, cy, cz);
    puff.scale.y = 0.4;
    cloud.add(puff);
  });
  cloud.position.set(x, y, z);
  cloud.scale.setScalar(scale);
  scene.add(cloud);
  return cloud;
}

function createField(THREE, scene, isMobile) {
  const terrain = new THREE.Mesh(
    terrainGeometry(THREE, 40, 30, isMobile ? 20 : 38, isMobile ? 16 : 28),
    new THREE.MeshStandardMaterial({ color: 0x58784e, roughness: 1, metalness: 0 }),
  );
  terrain.position.y = -0.25;
  terrain.receiveShadow = true;
  scene.add(terrain);

  const furrows = new THREE.Group();
  const furrowMaterial = new THREE.MeshStandardMaterial({ color: 0x816943, roughness: 1 });
  for (let row = 0; row < 17; row += 1) {
    const line = new THREE.Mesh(new THREE.BoxGeometry(26, 0.035, 0.12), furrowMaterial);
    line.position.set(0, -0.05, -7.7 + row * 0.95);
    furrows.add(line);
  }
  scene.add(furrows);

  const rowCount = isMobile ? 8 : 14;
  const plantsPerRow = isMobile ? 16 : 25;
  const count = rowCount * plantsPerRow;
  const cropGroup = new THREE.Group();
  const stem = new THREE.InstancedMesh(
    new THREE.CylinderGeometry(0.035, 0.065, 1, 5),
    new THREE.MeshStandardMaterial({ color: 0x7c9650, roughness: 0.9 }),
    count,
  );
  const leafGeometry = new THREE.ConeGeometry(0.11, 0.54, 4);
  const leaf = new THREE.InstancedMesh(
    leafGeometry,
    new THREE.MeshStandardMaterial({ color: 0x71975b, roughness: 0.9 }),
    count * 4,
  );
  const transform = new THREE.Object3D();
  let stemIndex = 0;
  let leafIndex = 0;
  for (let row = 0; row < rowCount; row += 1) {
    const z = -6.9 + row * (13.8 / Math.max(1, rowCount - 1));
    for (let plant = 0; plant < plantsPerRow; plant += 1) {
      const x = -11.5 + plant * (23 / Math.max(1, plantsPerRow - 1)) + (row % 2) * 0.18;
      const height = 0.78 + ((row * 7 + plant * 3) % 8) * 0.075;
      transform.position.set(x, height / 2, z);
      transform.scale.set(1, height, 1);
      transform.rotation.set(0, 0, 0);
      transform.updateMatrix();
      stem.setMatrixAt(stemIndex, transform.matrix);
      const leafColor = new THREE.Color(row % 3 === 0 ? 0x8ca260 : row % 3 === 1 ? 0x789452 : 0x9aa966);
      for (let side = 0; side < 4; side += 1) {
        const angle = (side / 4) * Math.PI * 2 + ((plant + row) % 3) * 0.12;
        transform.position.set(x + Math.cos(angle) * 0.16, height * 0.55, z + Math.sin(angle) * 0.16);
        transform.rotation.set(Math.sin(angle) * 0.42, angle, Math.cos(angle) * 0.55);
        transform.scale.set(0.76, 0.82 + (side % 2) * 0.16, 0.78);
        transform.updateMatrix();
        leaf.setMatrixAt(leafIndex, transform.matrix);
        leaf.setColorAt(leafIndex, leafColor);
        leafIndex += 1;
      }
      stemIndex += 1;
    }
  }
  stem.instanceMatrix.needsUpdate = true;
  leaf.instanceMatrix.needsUpdate = true;
  if (leaf.instanceColor) leaf.instanceColor.needsUpdate = true;
  cropGroup.add(stem, leaf);
  scene.add(cropGroup);

  const sun = new THREE.Mesh(
    new THREE.SphereGeometry(1.2, 20, 14),
    new THREE.MeshBasicMaterial({ color: 0xf3cd82 }),
  );
  sun.position.set(8.5, 8.6, -9.5);
  scene.add(sun);
  const clouds = [
    makeCloud(THREE, scene, 3, 9, -11, 1.15),
    makeCloud(THREE, scene, -8, 7.4, -10, 0.8),
  ];
  return { cropGroup, clouds };
}

function createPlant(THREE, scene, element) {
  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(2.7, 28),
    new THREE.MeshStandardMaterial({ color: 0x77905d, roughness: 1 }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.13;
  scene.add(ground);

  const stage = (element.dataset.stage || '').toLowerCase();
  const progress = Math.max(0, Math.min(100, Number(element.dataset.progress || 0)));
  let height = 0.75 + (progress / 100) * 1.5;
  if (stage.includes('germination')) height = 0.62;
  if (stage.includes('seedling')) height = 0.95;
  if (stage.includes('flower')) height = Math.max(height, 2.15);
  if (stage.includes('maturity') || stage.includes('grain')) height = Math.max(height, 2.35);

  const plant = new THREE.Group();
  const stem = new THREE.Mesh(
    new THREE.CylinderGeometry(0.065, 0.12, height, 7),
    new THREE.MeshStandardMaterial({ color: 0x55784b, roughness: 0.9 }),
  );
  stem.position.y = height / 2;
  plant.add(stem);
  const leafMaterial = new THREE.MeshStandardMaterial({ color: 0x6c9255, roughness: 0.9, side: THREE.DoubleSide });
  const leafCount = Math.max(3, Math.round(3 + progress / 13));
  const leafNodes = [];
  for (let index = 0; index < leafCount; index += 1) {
    const level = 0.25 + (index / leafCount) * height * 0.78;
    const angle = index * 2.399;
    const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.5, 9, 6), leafMaterial);
    leaf.scale.set(0.16, 0.52, 0.075);
    leaf.position.set(Math.cos(angle) * 0.08, level, Math.sin(angle) * 0.08);
    leaf.rotation.z = Math.cos(angle) * 0.9;
    leaf.rotation.y = angle;
    plant.add(leaf);
    leafNodes.push({ node: leaf, rotation: leaf.rotation.z });
  }
  if (stage.includes('flower') || stage.includes('maturity')) {
    const flower = new THREE.Mesh(
      new THREE.SphereGeometry(0.24, 10, 8),
      new THREE.MeshStandardMaterial({ color: stage.includes('maturity') ? 0xd9b35c : 0xe9d58a, roughness: 0.8 }),
    );
    flower.position.y = height + 0.05;
    plant.add(flower);
  }
  plant.position.y = -0.05;
  scene.add(plant);
  return { plant, leafNodes };
}

async function initializeScene(element) {
  try {
    const THREE = await import(THREE_MODULE);
    const canvas = element.querySelector('canvas');
    const rect = element.getBoundingClientRect();
    if (!canvas || rect.width < 2 || rect.height < 2) throw new Error('Scene has no visible area');

    const isMobile = matchMedia('(max-width: 767px)').matches;
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(element.dataset.farmScene === 'plant' ? 37 : 42, rect.width / rect.height, 0.1, 90);
    if (element.dataset.farmScene === 'plant') camera.position.set(4.3, 4.5, 6.8);
    else camera.position.set(0, 10.3, 19.5);
    camera.lookAt(0, element.dataset.farmScene === 'plant' ? 1.15 : 0, 0);

    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: !isMobile,
      powerPreference: 'low-power',
      depth: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, isMobile ? 1.2 : 1.65));
    renderer.setSize(rect.width, rect.height, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    addLighting(THREE, scene);

    let movingObjects;
    if (element.dataset.farmScene === 'plant') movingObjects = createPlant(THREE, scene, element);
    else movingObjects = createField(THREE, scene, isMobile);

    let pointerX = 0;
    let pointerY = 0;
    let frame = 0;
    let elapsed = 0;
    let visible = true;
    let disposed = false;
    const resizeObserver = new ResizeObserver(() => {
      const bounds = element.getBoundingClientRect();
      if (bounds.width < 2 || bounds.height < 2) return;
      camera.aspect = bounds.width / bounds.height;
      camera.updateProjectionMatrix();
      renderer.setSize(bounds.width, bounds.height, false);
      renderOnce();
    });
    resizeObserver.observe(element);

    const onPointerMove = (event) => {
      const bounds = element.getBoundingClientRect();
      pointerX = ((event.clientX - bounds.left) / bounds.width - 0.5) * 0.12;
      pointerY = ((event.clientY - bounds.top) / bounds.height - 0.5) * 0.07;
    };
    if (!isMobile && element.dataset.farmScene === 'field') element.addEventListener('pointermove', onPointerMove, { passive: true });

    function renderOnce() {
      if (disposed) return;
      camera.position.x += (pointerX * (element.dataset.farmScene === 'plant' ? 1 : 10) - camera.position.x * 0.0004);
      camera.position.y += (-pointerY * 4 - (camera.position.y - (element.dataset.farmScene === 'plant' ? 4.5 : 10.3)) * 0.0004);
      camera.lookAt(0, element.dataset.farmScene === 'plant' ? 1.1 : 0, 0);
      renderer.render(scene, camera);
    }

    function animate() {
      if (disposed || !visible || document.hidden) return;
      frame = requestAnimationFrame(animate);
      elapsed += 0.008;
      if (movingObjects.cropGroup) movingObjects.cropGroup.rotation.z = Math.sin(elapsed) * 0.012;
      if (movingObjects.plant) {
        movingObjects.plant.rotation.z = Math.sin(elapsed) * 0.012;
        movingObjects.leafNodes.forEach(({ node, rotation }, index) => {
          node.rotation.z = rotation + Math.sin(elapsed + index * 0.4) * 0.018;
        });
      }
      if (movingObjects.clouds) movingObjects.clouds.forEach((cloud, index) => {
        cloud.position.x += 0.0015 * (index % 2 ? -1 : 1);
        if (cloud.position.x > 13) cloud.position.x = -13;
        if (cloud.position.x < -13) cloud.position.x = 13;
      });
      renderOnce();
    }

    const visibilityObserver = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible && !reducedMotion && !frame) animate();
      if (!visible && frame) {
        cancelAnimationFrame(frame);
        frame = 0;
      }
      if (visible && reducedMotion) renderOnce();
    }, { threshold: 0.02 });
    visibilityObserver.observe(element);
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && frame) {
        cancelAnimationFrame(frame);
        frame = 0;
      } else if (!document.hidden && visible && !reducedMotion && !frame) animate();
    });
    element.addEventListener('agri-scene-dispose', () => {
      disposed = true;
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      visibilityObserver.disconnect();
      renderer.dispose();
    }, { once: true });
    element.dataset.sceneState = 'ready';
    renderOnce();
    if (!reducedMotion && visible) animate();
  } catch (_) {
    setFallback(element);
  }
}

if ('IntersectionObserver' in window) {
  const loader = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      loader.unobserve(entry.target);
      initializeScene(entry.target);
    });
  }, { rootMargin: '120px 0px', threshold: 0.01 });
  scenes.forEach((scene) => loader.observe(scene));
} else {
  scenes.forEach(initializeScene);
}
