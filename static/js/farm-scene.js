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
  const bedShape = new THREE.Shape();
  bedShape.moveTo(-1.25, -0.7);
  bedShape.lineTo(1.25, -0.7);
  bedShape.quadraticCurveTo(1.42, -0.7, 1.42, -0.53);
  bedShape.lineTo(1.42, 0.53);
  bedShape.quadraticCurveTo(1.42, 0.7, 1.25, 0.7);
  bedShape.lineTo(-1.25, 0.7);
  bedShape.quadraticCurveTo(-1.42, 0.7, -1.42, 0.53);
  bedShape.lineTo(-1.42, -0.53);
  bedShape.quadraticCurveTo(-1.42, -0.7, -1.25, -0.7);
  const ground = new THREE.Mesh(
    new THREE.ShapeGeometry(bedShape, 8),
    new THREE.MeshStandardMaterial({ color: 0x806b4e, roughness: 1, side: THREE.DoubleSide }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.12;
  scene.add(ground);

  const stage = (element.dataset.stage || '').toLowerCase();
  const progress = Math.max(0, Math.min(100, Number(element.dataset.progress || 0)));
  let height = 0.9 + (progress / 100) * 0.85;
  if (stage.includes('germination')) height = 0.48;
  if (stage.includes('seedling') || stage.includes('emergence')) height = 0.78;
  if (stage.includes('flower')) height = Math.max(height, 1.65);
  if (stage.includes('maturity') || stage.includes('grain')) height = Math.max(height, 1.75);

  const plant = new THREE.Group();
  const driftParticles = [];
  const leafMaterial = new THREE.MeshStandardMaterial({ color: 0x62864d, roughness: 0.9, side: THREE.DoubleSide });
  const leafShape = new THREE.Shape();
  leafShape.moveTo(0, 0);
  leafShape.quadraticCurveTo(0.09, 0.22, 0.28, 0.52);
  leafShape.quadraticCurveTo(0.42, 0.88, 0.34, 1);
  leafShape.quadraticCurveTo(0.12, 0.84, 0.08, 0.55);
  leafShape.quadraticCurveTo(-0.025, 0.24, 0, 0);
  const leafGeometry = new THREE.ShapeGeometry(leafShape, 8);
  const stemMaterial = new THREE.MeshStandardMaterial({ color: 0x71904f, roughness: 0.9 });
  const grainMaterial = new THREE.MeshStandardMaterial({
    color: stage.includes('maturity') || stage.includes('grain') ? 0xd6ad55 : 0x9eae62,
    roughness: 0.82,
  });
  const grainGeometry = new THREE.SphereGeometry(0.1, 8, 6);
  const leafCount = Math.max(3, Math.round(3 + progress / 20));
  const leafNodes = [];
  const tillerOffsets = [[0, 0], [-0.27, -0.16], [0.26, -0.14], [-0.19, 0.22], [0.2, 0.2]];
  const tillerCount = Math.min(tillerOffsets.length, 2 + Math.floor(progress / 25));
  for (let tiller = 0; tiller < tillerCount; tiller += 1) {
    const [offsetX, offsetZ] = tillerOffsets[tiller];
    const stemHeight = height * (tiller === 0 ? 1 : 0.76 + (tiller % 2) * 0.05);
    const headOffset = 0.14 + (tiller % 2) * 0.06;
    const stemCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(offsetX, -0.05, offsetZ),
      new THREE.Vector3(offsetX - headOffset * 0.28, stemHeight * 0.5, offsetZ),
      new THREE.Vector3(offsetX + headOffset, stemHeight, offsetZ),
    ]);
    const stem = new THREE.Mesh(new THREE.TubeGeometry(stemCurve, 12, 0.035, 6, false), stemMaterial);
    plant.add(stem);
    for (let index = 0; index < leafCount; index += 1) {
      const level = 0.12 + (index / leafCount) * stemHeight * 0.68;
      const angle = index * 2.399 + tiller * 1.1;
      const leaf = new THREE.Mesh(leafGeometry, leafMaterial);
      leaf.position.set(offsetX, level, offsetZ);
      leaf.rotation.set(-0.13, angle, -0.48 + (index % 2) * 0.18);
      const length = stemHeight * (0.48 + (index % 3) * 0.08);
      leaf.scale.setScalar(length);
      plant.add(leaf);
      leafNodes.push({ node: leaf, rotation: leaf.rotation.z });
    }

    if (stage.includes('flower') || stage.includes('grain') || stage.includes('maturity')) {
      const head = new THREE.CatmullRomCurve3([
        new THREE.Vector3(offsetX + headOffset, stemHeight, offsetZ),
        new THREE.Vector3(offsetX + headOffset + 0.08, stemHeight - 0.12, offsetZ),
        new THREE.Vector3(offsetX + headOffset + 0.25, stemHeight - 0.38, offsetZ + 0.03),
      ]);
      plant.add(new THREE.Mesh(new THREE.TubeGeometry(head, 10, 0.018, 5, false), stemMaterial));
      for (let kernel = 0; kernel < 8; kernel += 1) {
        const t = 0.12 + kernel * 0.105;
        const center = head.getPoint(t);
        const side = kernel % 2 ? 1 : -1;
        const grain = new THREE.Mesh(grainGeometry, grainMaterial);
        grain.position.set(center.x + side * 0.075, center.y, center.z + side * 0.025);
        grain.scale.set(0.58, 1.45, 0.62);
        grain.rotation.z = -0.42;
        plant.add(grain);
      }
    }
  }
  plant.position.y = -0.05;
  scene.add(plant);
  const pollenMaterial = new THREE.MeshBasicMaterial({
    color: 0xffe2a0,
    transparent: true,
    opacity: 0.72,
    depthWrite: false,
  });
  const pollenGeometry = new THREE.SphereGeometry(0.025, 6, 5);
  for (let index = 0; index < 12; index += 1) {
    const particle = new THREE.Mesh(pollenGeometry, pollenMaterial);
    const x = -1.25 + ((index * 37) % 100) / 100 * 2.5;
    const y = 0.25 + ((index * 23) % 100) / 100 * 2.2;
    const z = -0.85 + ((index * 41) % 100) / 100 * 1.7;
    particle.position.set(x, y, z);
    particle.scale.setScalar(0.65 + (index % 4) * 0.18);
    scene.add(particle);
    driftParticles.push({ node: particle, x, y, z, phase: index * 0.83 });
  }
  return { plant, leafNodes, driftParticles };
}

function createRecommendationLoader(THREE, scene) {
  const soil = new THREE.Mesh(
    new THREE.CylinderGeometry(1.05, 1.18, 0.24, 32),
    new THREE.MeshStandardMaterial({ color: 0x9b7648, roughness: 1 }),
  );
  soil.position.y = -0.08;
  scene.add(soil);

  const plant = new THREE.Group();
  const stemCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0.02, 0),
    new THREE.Vector3(-0.05, 0.42, 0),
    new THREE.Vector3(0.02, 0.98, 0),
  ]);
  plant.add(new THREE.Mesh(
    new THREE.TubeGeometry(stemCurve, 12, 0.045, 6, false),
    new THREE.MeshStandardMaterial({ color: 0x508052, roughness: 0.85 }),
  ));
  const leafShape = new THREE.Shape();
  leafShape.moveTo(0, 0);
  leafShape.quadraticCurveTo(0.18, 0.16, 0.58, 0.36);
  leafShape.quadraticCurveTo(0.29, 0.48, 0, 0);
  const leafGeometry = new THREE.ShapeGeometry(leafShape, 8);
  const leafMaterial = new THREE.MeshStandardMaterial({
    color: 0x68a765,
    roughness: 0.8,
    side: THREE.DoubleSide,
  });
  [[-0.02, 0.28, 0.42], [0.02, 0.53, -0.5], [0, 0.74, 0.48]].forEach(([x, y, rotation]) => {
    const leaf = new THREE.Mesh(leafGeometry, leafMaterial);
    leaf.position.set(x, y, 0);
    leaf.rotation.set(0, rotation * 0.3, rotation);
    plant.add(leaf);
  });
  const seed = new THREE.Mesh(
    new THREE.SphereGeometry(0.16, 12, 8),
    new THREE.MeshStandardMaterial({ color: 0xe3b663, roughness: 0.7 }),
  );
  seed.position.set(0, 0.16, 0.1);
  plant.add(seed);
  scene.add(plant);

  const ringMaterial = new THREE.MeshBasicMaterial({
    color: 0xe3c36d,
    transparent: true,
    opacity: 0.72,
  });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(1.42, 0.018, 6, 64), ringMaterial);
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 0.55;
  scene.add(ring);
  const orbit = new THREE.Group();
  const orbitDotGeometry = new THREE.SphereGeometry(0.045, 8, 6);
  const orbitDotMaterial = new THREE.MeshBasicMaterial({ color: 0xf4d687 });
  for (let index = 0; index < 6; index += 1) {
    const angle = (index / 6) * Math.PI * 2;
    const dot = new THREE.Mesh(orbitDotGeometry, orbitDotMaterial);
    dot.position.set(Math.cos(angle) * 1.42, 0.55, Math.sin(angle) * 1.42);
    orbit.add(dot);
  }
  scene.add(orbit);
  return { loaderPlant: plant, loaderRing: ring, loaderOrbit: orbit, loaderSeed: seed };
}

function createAmbient(THREE, scene, aspect) {
  const group = new THREE.Group();
  const leafShape = new THREE.Shape();
  leafShape.moveTo(0, 0);
  leafShape.quadraticCurveTo(0.42, 0.06, 0.82, 0.38);
  leafShape.quadraticCurveTo(0.5, 0.52, 0, 0);
  const leafGeometry = new THREE.ShapeGeometry(leafShape, 8);
  const leafColors = [0x4e8a64, 0x6ca786, 0xb78a4b, 0x5f9a91];
  const viewWidth = 13.8 * aspect;
  const leaves = [];
  for (let index = 0; index < 8; index += 1) {
    const material = new THREE.MeshBasicMaterial({
      color: leafColors[index % leafColors.length],
      transparent: true,
      opacity: 0.38,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const leaf = new THREE.Mesh(leafGeometry, material);
    const x = ((index + 0.5) / 8 - 0.5) * viewWidth * 0.95;
    const y = Math.sin(index * 2.1) * 3.8;
    const z = -1.5 - (index % 3) * 0.75;
    leaf.position.set(x, y, z);
    leaf.rotation.set((index % 3 - 1) * 0.12, (index % 2 ? 1 : -1) * 0.3, index * 1.7);
    leaf.scale.setScalar(0.75 + (index % 4) * 0.28);
    group.add(leaf);
    leaves.push({ node: leaf, x, y, z, rotation: leaf.rotation.z, phase: index * 0.9 });
  }
  scene.add(group);

  const particlePositions = [];
  for (let index = 0; index < 28; index += 1) {
    particlePositions.push(
      ((index * 37) % 100) / 100 * viewWidth - viewWidth / 2,
      ((index * 23) % 100) / 100 * 9 - 4.5,
      -0.5 - ((index * 13) % 30) / 10,
    );
  }
  const particleGeometry = new THREE.BufferGeometry();
  particleGeometry.setAttribute('position', new THREE.Float32BufferAttribute(particlePositions, 3));
  const particles = new THREE.Points(
    particleGeometry,
    new THREE.PointsMaterial({
      color: 0xe6c783,
      size: 0.075,
      transparent: true,
      opacity: 0.6,
      sizeAttenuation: true,
      depthWrite: false,
    }),
  );
  scene.add(particles);
  return { ambientGroup: group, ambientLeaves: leaves, ambientParticles: particles };
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
    const plantScene = element.dataset.farmScene === 'plant';
    const ambientScene = element.dataset.farmScene === 'ambient';
    const loaderScene = element.dataset.farmScene === 'loader';
    const camera = new THREE.PerspectiveCamera(plantScene || loaderScene ? 37 : 42, rect.width / rect.height, 0.1, 90);
    if (plantScene) camera.position.set(3.2, 3.4, 5);
    else if (loaderScene) camera.position.set(3.1, 2.8, 5.4);
    else if (ambientScene) camera.position.set(0, 0, 15);
    else camera.position.set(0, 10.3, 19.5);
    camera.lookAt(0, plantScene ? 0.95 : loaderScene ? 0.55 : 0, 0);

    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: !isMobile,
      powerPreference: 'low-power',
      depth: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, ambientScene ? 1 : isMobile ? 1.2 : 1.65));
    renderer.setSize(rect.width, rect.height, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    addLighting(THREE, scene);

    let movingObjects;
    if (plantScene) movingObjects = createPlant(THREE, scene, element);
    else if (loaderScene) movingObjects = createRecommendationLoader(THREE, scene);
    else if (ambientScene) movingObjects = createAmbient(THREE, scene, rect.width / rect.height);
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
    if (!isMobile) element.addEventListener('pointermove', onPointerMove, { passive: true });

    function renderOnce() {
      if (disposed) return;
      const baseX = plantScene ? 3.2 : 0;
      const baseY = plantScene ? 3.4 : loaderScene ? 2.8 : ambientScene ? 0 : 10.3;
      const pointerScale = plantScene || loaderScene ? 4 : ambientScene ? 0.8 : 10;
      camera.position.x += (baseX + pointerX * pointerScale - camera.position.x) * 0.04;
      camera.position.y += (baseY - pointerY * (plantScene || loaderScene ? 1.8 : ambientScene ? 0.5 : 4) - camera.position.y) * 0.04;
      camera.lookAt(0, plantScene ? 0.95 : loaderScene ? 0.55 : 0, 0);
      renderer.render(scene, camera);
    }

    function animate() {
      if (disposed || !visible || document.hidden) return;
      frame = requestAnimationFrame(animate);
      elapsed += 0.008;
      if (movingObjects.cropGroup) movingObjects.cropGroup.rotation.z = Math.sin(elapsed) * 0.012;
      if (movingObjects.plant) {
        movingObjects.plant.rotation.z = Math.sin(elapsed) * 0.028;
        movingObjects.leafNodes.forEach(({ node, rotation }, index) => {
          node.rotation.z = rotation + Math.sin(elapsed + index * 0.4) * 0.04;
        });
        movingObjects.driftParticles.forEach(({ node, x, y, z, phase }) => {
          node.position.set(
            x + Math.sin(elapsed * 0.34 + phase) * 0.12,
            y + Math.sin(elapsed * 0.52 + phase) * 0.12,
            z + Math.cos(elapsed * 0.3 + phase) * 0.08,
          );
        });
      }
      if (movingObjects.ambientLeaves) {
        movingObjects.ambientGroup.rotation.y = pointerX * 0.65;
        movingObjects.ambientGroup.rotation.x = -pointerY * 0.65;
        movingObjects.ambientLeaves.forEach(({ node, x, y, z, rotation, phase }) => {
          node.position.set(x + Math.sin(elapsed * 0.24 + phase) * 0.16, y + Math.sin(elapsed * 0.38 + phase) * 0.2, z);
          node.rotation.z = rotation + Math.sin(elapsed * 0.3 + phase) * 0.08;
        });
        movingObjects.ambientParticles.position.y = Math.sin(elapsed * 0.2) * 0.1;
      }
      if (movingObjects.loaderPlant) {
        movingObjects.loaderPlant.rotation.y = Math.sin(elapsed * 0.35) * 0.16;
        movingObjects.loaderPlant.rotation.z = Math.sin(elapsed * 0.75) * 0.035;
        movingObjects.loaderSeed.scale.setScalar(1 + Math.sin(elapsed * 1.8) * 0.06);
        movingObjects.loaderRing.rotation.z += 0.006;
        movingObjects.loaderOrbit.rotation.y += 0.012;
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
