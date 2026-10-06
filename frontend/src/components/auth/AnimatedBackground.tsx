'use client';

import { motion } from 'framer-motion';

interface AnimatedBackgroundProps {
  particleCount?: number;
  className?: string;
}

export default function AnimatedBackground({
  particleCount = 20,
  className = ""
}: AnimatedBackgroundProps) {
  return (
    <div className={`absolute inset-0 overflow-hidden ${className}`}>
      {Array.from({ length: particleCount }).map((_, i) => {
        // Generate consistent values for hydration
        const width = 3;
        const height = 3;
        const left = `${(i * 100) / particleCount}%`;
        const top = `${((i * 7) % 100)}%`;

        return (
          <motion.div
            key={i}
            className="absolute rounded-full bg-white/10"
            style={{
              width,
              height,
              left: `${left}%`,
              top: `${top}%`,
            }}
            initial={{ opacity: 0.3, scale: 1 }}
            animate={{
              y: [0, -20, 0],
              opacity: [0.3, 0.7, 0.3],
              scale: [1, 1.1, 1],
            }}
            transition={{
              duration: 4 + (i % 4),
              repeat: Infinity,
              delay: (i % 2),
            }}
          />
        );
      })}
    </div>
  );
}