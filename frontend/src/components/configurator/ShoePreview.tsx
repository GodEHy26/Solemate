import { OrbitControls, RoundedBox } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';

interface Props {
  colors: Record<string, string>;
  heroColor: string;
}

/**
 * Stylised parametric shoe so material/colour choices are visible immediately.
 * Replace with real per-model GLB assets once the line-up is final.
 */
export function ShoePreview({ colors, heroColor }: Props) {
  const outsole = colors.outsole ?? '#111111';
  const midsole = colors.midsole ?? '#f2efe8';
  const upper = colors.upper ?? heroColor;
  const laces = colors.laces ?? '#f2efe8';
  return (
    <div className="viewer" style={{ height: 300 }}>
      <Canvas camera={{ position: [2.6, 1.6, 2.8], fov: 38 }}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[3, 5, 2]} intensity={1.3} />
        <directionalLight position={[-3, 2, -2]} intensity={0.4} />
        <group position={[0, -0.35, 0]}>
          {/* outsole */}
          <RoundedBox args={[2.6, 0.16, 1.0]} radius={0.08} smoothness={4} position={[0, 0.08, 0]}>
            <meshStandardMaterial color={outsole} roughness={0.9} />
          </RoundedBox>
          {/* midsole */}
          <RoundedBox args={[2.55, 0.22, 0.95]} radius={0.1} smoothness={4} position={[0, 0.27, 0]}>
            <meshStandardMaterial color={midsole} roughness={0.6} />
          </RoundedBox>
          {/* upper: elongated capsule-ish body */}
          <mesh position={[0.1, 0.62, 0]} scale={[1.25, 0.42, 0.46]}>
            <sphereGeometry args={[1, 40, 24]} />
            <meshStandardMaterial color={upper} roughness={0.75} />
          </mesh>
          {/* heel collar */}
          <mesh position={[-0.95, 0.85, 0]} scale={[0.32, 0.42, 0.42]}>
            <sphereGeometry args={[1, 24, 16]} />
            <meshStandardMaterial color={upper} roughness={0.75} />
          </mesh>
          {/* laces */}
          {[0.55, 0.3, 0.05, -0.2].map((x, i) => (
            <mesh key={i} position={[x, 0.98 - i * 0.02, 0]} rotation={[Math.PI / 2, 0, Math.PI / 2 + 0.25]}>
              <cylinderGeometry args={[0.02, 0.02, 0.42, 10]} />
              <meshStandardMaterial color={laces} />
            </mesh>
          ))}
        </group>
        <gridHelper args={[6, 24, '#2b3140', '#1c2029']} position={[0, -0.36, 0]} />
        <OrbitControls enablePan={false} minDistance={2} maxDistance={6} autoRotate autoRotateSpeed={1.2} />
      </Canvas>
    </div>
  );
}
