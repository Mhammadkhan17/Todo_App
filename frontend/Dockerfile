# Multi-stage build for Next.js frontend

# Development stage
FROM node:20-alpine AS development

# Set working directory
WORKDIR /app

# Install bash and other dependencies
RUN apk add --no-cache bash

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy the rest of the application code
COPY . .

# Expose port 3000
EXPOSE 3000

# Development command
CMD ["npm", "run", "dev"]

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine AS production

# Set working directory
WORKDIR /app

# Install bash and other dependencies
RUN apk add --no-cache bash dumb-init

# Copy package files
COPY package.json package-lock.json* ./

# Install only production dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy built application from builder stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Create non-root user for security
RUN addgroup -g 1001 -S nextjs && \
    adduser -S nextjs -u 1001

# Change ownership of the app directory
RUN chown -R nextjs:nextjs /app
USER nextjs

# Expose port 3000
EXPOSE 3000

# Use dumb-init to handle PID 1 issues
ENTRYPOINT ["dumb-init", "--"]

# Start the production server
CMD ["npm", "start"]