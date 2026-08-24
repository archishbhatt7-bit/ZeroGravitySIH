"""Collision probability estimation.

Implements multiple methods for computing the probability of collision (Pc)
given conjunction geometry and covariance data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)
from numpy.typing import NDArray
from scipy.integrate import dblquad


class PcMethod(Enum):
    """Collision probability calculation methods."""

    FOSTER_1992 = "foster_1992"
    MONTE_CARLO = "monte_carlo"


@dataclass
class PcResult:
    """Result of a collision probability calculation.

    Attributes:
        probability: Estimated collision probability.
        method: Method used for calculation.
        combined_hard_body_radius_m: Combined hard-body radius in meters.
        mahalanobis_distance: Mahalanobis distance (if applicable).
        samples: Number of samples used (for Monte Carlo).
    """

    probability: float
    method: PcMethod
    combined_hard_body_radius_m: float
    mahalanobis_distance: float | None = None
    samples: int | None = None


def _relative_state(
    pos1: NDArray, vel1: NDArray, pos2: NDArray, vel2: NDArray
) -> tuple[NDArray, NDArray]:
    """Compute relative position and velocity.
    
    Args:
        pos1: Primary position vector (km)
        vel1: Primary velocity vector (km/s)
        pos2: Secondary position vector (km)
        vel2: Secondary velocity vector (km/s)
        
    Returns:
        Tuple of (relative_position, relative_velocity)
    """
    rel_pos = pos2 - pos1
    rel_vel = vel2 - vel1
    return rel_pos, rel_vel


def _project_to_bplane(
    rel_pos: NDArray, rel_vel: NDArray, cov_combined: NDArray
) -> tuple[NDArray, NDArray]:
    """Project miss vector and combined covariance onto the B-plane.
    
    B-plane is perpendicular to relative velocity.
    Define: z_hat = rel_vel / |rel_vel| (along-track)
    Pick x_hat perpendicular to z_hat (e.g., cross with [0,0,1] or rel_pos)
    y_hat = z_hat × x_hat
    
    Project rel_pos onto [x_hat, y_hat] → 2D miss vector
    Project cov_combined: C_2d = P @ cov_pos @ P.T where P is the 2x3 projection matrix
    
    Args:
        rel_pos: Relative position vector (3,)
        rel_vel: Relative velocity vector (3,)
        cov_combined: Combined 6x6 covariance matrix (position+velocity)
        
    Returns:
        Tuple of (miss_2d: shape (2,), cov_2d: shape (2,2))
    """
    # Extract position covariance (upper-left 3x3 block)
    cov_pos = cov_combined[:3, :3]
    
    # Check for zero or very small relative velocity
    rel_vel_norm = np.linalg.norm(rel_vel)
    if rel_vel_norm < 1e-10:
        # No relative velocity - objects are moving together
        # Use arbitrary B-plane (any two perpendicular directions)
        # Project the full 3D position into a 2D plane
        # Use first two components as a simple projection
        miss_2d = rel_pos[:2]
        cov_2d = cov_pos[:2, :2]
        return miss_2d, cov_2d
    
    # Define B-plane coordinate system
    # z_hat: along relative velocity (excluded from B-plane)
    z_hat = rel_vel / rel_vel_norm
    
    # x_hat: perpendicular to z_hat
    # Try cross with [0, 0, 1] first, fallback to [1, 0, 0] if parallel
    up = np.array([0.0, 0.0, 1.0])
    x_hat = np.cross(z_hat, up)
    
    if np.linalg.norm(x_hat) < 1e-10:
        # z_hat is nearly parallel to [0, 0, 1], use [1, 0, 0] instead
        up = np.array([1.0, 0.0, 0.0])
        x_hat = np.cross(z_hat, up)
    
    x_hat = x_hat / np.linalg.norm(x_hat)
    
    # y_hat: completes right-handed coordinate system
    y_hat = np.cross(z_hat, x_hat)
    
    # Projection matrix P: 2x3 matrix [x_hat; y_hat]
    P = np.vstack([x_hat, y_hat])
    
    # Project miss vector onto B-plane
    miss_2d = P @ rel_pos
    
    # Project covariance onto B-plane
    cov_2d = P @ cov_pos @ P.T
    
    return miss_2d, cov_2d


def compute_pc_foster(
    miss_2d: NDArray,
    cov_2d: NDArray,
    hard_body_radius: float,
) -> float:
    """Compute Pc via numerical integration of bivariate normal over hard-body disk.
    
    Uses scipy.integrate.dblquad in polar coordinates to compute:
        Pc = ∫∫_circle PDF(x, y) dx dy
    where PDF is the 2D Gaussian with covariance cov_2d centered at miss_2d.
    
    Args:
        miss_2d: 2D miss vector in B-plane (km)
        cov_2d: 2x2 covariance matrix in B-plane (km²)
        hard_body_radius: Combined hard-body radius (km)
        
    Returns:
        Collision probability (0 to 1)
    """
    # Check for singular covariance
    det = np.linalg.det(cov_2d)
    if det < 1e-20:
        # Covariance is nearly singular - probability is essentially 0
        return 0.0
    
    # Invert covariance matrix
    cov_inv = np.linalg.inv(cov_2d)
    
    # Mean of the distribution (center of miss ellipse)
    mx, my = miss_2d
    
    # Normalization factor for 2D Gaussian
    norm_factor = 1.0 / (2.0 * np.pi * np.sqrt(det))
    
    # Define the 2D Gaussian PDF in Cartesian coordinates
    def pdf_cartesian(x, y):
        r = np.array([x - mx, y - my])
        exponent = -0.5 * (r @ cov_inv @ r)
        return norm_factor * np.exp(exponent)
    
    # Integrate over a circular disk using polar coordinates
    # x = r * cos(theta), y = r * sin(theta)
    # Jacobian: r
    # Integrate: ∫_0^R ∫_0^2π PDF(r*cos(θ), r*sin(θ)) * r dθ dr
    
    def integrand_polar(theta, r):
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        return pdf_cartesian(x, y) * r  # r is the Jacobian
    
    # Perform double integration in polar coordinates
    # dblquad integrates over theta first (inner), then r (outer)
    result, error = dblquad(
        integrand_polar,
        0.0, hard_body_radius,  # r from 0 to hard_body_radius
        lambda r: 0.0, lambda r: 2.0 * np.pi,  # theta from 0 to 2π
        epsabs=1e-10, epsrel=1e-6
    )
    
    # Clamp to [0, 1]
    return np.clip(result, 0.0, 1.0)


def compute_pc_monte_carlo(
    rel_pos: NDArray,
    rel_vel: NDArray | None,
    cov_combined: NDArray,
    hard_body_radius: float,
    n_samples: int = 100_000,
    seed: int = 42,
) -> float:
    """Monte Carlo Pc estimation.
    
    Sample positions from each object's covariance and count how many
    samples result in a collision. Projects samples onto B-plane (perpendicular
    to relative velocity) to match Foster method.
    
    Args:
        rel_pos: Relative position vector (km)
        rel_vel: Relative velocity vector (km/s)
        cov_combined: Combined 6x6 covariance matrix (position+velocity)
        hard_body_radius: Combined hard-body radius (km)
        n_samples: Number of Monte Carlo samples
        seed: Random seed for reproducibility
        
    Returns:
        Collision probability (0 to 1)
    """
    rng = np.random.default_rng(seed)
    
    # Extract position covariance (upper-left 3x3 block)
    cov_pos = cov_combined[:3, :3]
    
    # Check for singular covariance
    try:
        # Sample relative positions from the combined covariance
        # Distribution is centered at rel_pos
        samples_3d = rng.multivariate_normal(rel_pos, cov_pos, size=n_samples)
    except np.linalg.LinAlgError:
        # Singular covariance - cannot sample
        return 0.0
    
    # Project samples onto B-plane (perpendicular to relative velocity)
    # This matches the Foster method by ignoring along-track uncertainty
    rel_vel_norm = np.linalg.norm(rel_vel) if rel_vel is not None else 0.0
    if rel_vel_norm < 1e-10:
        # Zero relative velocity - use 3D distance
        distances = np.linalg.norm(samples_3d, axis=1)
    else:
        # Remove component along relative velocity
        z_hat = rel_vel / rel_vel_norm
        # For each sample, remove the along-track component
        along_track = np.dot(samples_3d, z_hat).reshape(-1, 1)
        samples_bplane = samples_3d - along_track * z_hat
        # Compute distances in B-plane
        distances = np.linalg.norm(samples_bplane, axis=1)
    
    # Count collisions
    collisions = np.sum(distances < hard_body_radius)
    
    return collisions / n_samples


def compute_pc(
    pos1_km: NDArray,
    vel1_km_s: NDArray,
    pos2_km: NDArray,
    vel2_km_s: NDArray,
    cov1: NDArray,
    cov2: NDArray,
    hard_body_radius_m: float = 20.0,
    method: PcMethod = PcMethod.FOSTER_1992,
    mc_samples: int = 100_000,
) -> PcResult:
    """Main entry point. Compute collision probability.
    
    Args:
        pos1_km: Primary position vector (km) in ECI
        vel1_km_s: Primary velocity vector (km/s) in ECI
        pos2_km: Secondary position vector (km) in ECI
        vel2_km_s: Secondary velocity vector (km/s) in ECI
        cov1: 6x6 covariance matrix for primary (position+velocity) in km, km/s
        cov2: 6x6 covariance matrix for secondary (position+velocity) in km, km/s
        hard_body_radius_m: Combined hard-body radius in meters
        method: Calculation method
        mc_samples: Number of samples for Monte Carlo method
    
    Returns:
        PcResult with collision probability and metadata
        
    Note:
        Combined covariance = cov1 + cov2 (assuming independence).
        Hard body radius is converted from meters to km internally.
    """
    # Convert hard body radius from meters to km
    hard_body_radius_km = hard_body_radius_m / 1000.0
    
    # Compute relative state
    rel_pos, rel_vel = _relative_state(pos1_km, vel1_km_s, pos2_km, vel2_km_s)
    
    # Combined covariance (assuming independence)
    cov_combined = cov1 + cov2
    
    # Compute Mahalanobis distance
    cov_pos = cov_combined[:3, :3]
    try:
        cov_pos_inv = np.linalg.inv(cov_pos)
        mahalanobis = np.sqrt(rel_pos @ cov_pos_inv @ rel_pos)
    except np.linalg.LinAlgError:
        mahalanobis = None
    
    # Compute Pc based on method
    if method == PcMethod.FOSTER_1992:
        # Project to B-plane
        miss_2d, cov_2d = _project_to_bplane(rel_pos, rel_vel, cov_combined)
        
        # Compute Pc using Foster method
        pc = compute_pc_foster(miss_2d, cov_2d, hard_body_radius_km)
        
        logger.debug("Pc computation complete: method=%s, Pc=%.2e", method.value, pc)
        return PcResult(
            probability=pc,
            method=method,
            combined_hard_body_radius_m=hard_body_radius_m,
            mahalanobis_distance=mahalanobis,
        )
    
    elif method == PcMethod.MONTE_CARLO:
        # Monte Carlo estimation
        pc = compute_pc_monte_carlo(
            rel_pos, rel_vel, cov_combined, hard_body_radius_km, n_samples=mc_samples
        )
        
        logger.debug("Pc computation complete: method=%s, Pc=%.2e", method.value, pc)
        return PcResult(
            probability=pc,
            method=method,
            combined_hard_body_radius_m=hard_body_radius_m,
            mahalanobis_distance=mahalanobis,
            samples=mc_samples,
        )
    
    else:
        raise ValueError(f"Unknown method: {method}")
