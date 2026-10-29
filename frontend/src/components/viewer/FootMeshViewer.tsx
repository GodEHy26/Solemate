import { Center, OrbitControls } from '@react-three/drei';
import { Canvas, useLoader } from '@react-three/fiber';
import { Component, Suspense, useMemo, type ReactNode } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

function FootModel({ url, color }: { url: string; color: string }) {
  const gltf = useLoader(GLTFLoader, url);
  const scene = useMemo(() => {
    const s = gltf.scene.clone(true);
    const material = new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0.05 });
    s.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) {
        const m = o as THREE.Mesh;
        m.material = material;
        m.castShadow = true;
        m.receiveShadow = true;
      }
    });
    return s;
  }, [gltf, color]);
  return (
    <group rotation={[-Math.PI / 2, 0, 0]} scale={0.01}>
      <primitive object={scene} />
    </group>
  );
}

class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? <div className="overlay-msg">Could not load the 3D model.</div> : this.props.children;
  }
}

export function FootMeshViewer({ url, color = '#e8c9a8' }: { url: string; color?: string }) {
  return (
    <div className="viewer">
      <Boundary>
        <Canvas shadows camera={{ position: [3.2, 2.2, 3.2], fov: 40 }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[4, 6, 3]} intensity={1.4} castShadow />
          <directionalLight position={[-4, 2, -3]} intensity={0.4} />
          <Suspense fallback={null}>
            <Center top>
              <FootModel url={url} color={color} />
            </Center>
          </Suspense>
          <gridHelper args={[6, 24, '#2b3140', '#1c2029']} position={[0, -0.001, 0]} />
          <OrbitControls enablePan={false} minDistance={1.5} maxDistance={8} autoRotate autoRotateSpeed={0.8} />
        </Canvas>
      </Boundary>
    </div>
  );
}
