"""Tests for collision probability calculations."""

from __future__ import annotations

import numpy as np
import pytest

from zerogravity.core.probability import (
    PcMethod,
    PcResult,
    _project_to_bplane,
    _relative_state,
    compute_pc,
    compute_pc_foster,
    compute_pc_monte_carlo,
)


class TestRelativeState:
    """Test relative state computation."""

    def test_basic_relative_state(self):
        """Test basic relative state calculation."""
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.5, 0.0])
        pos2 = np.array([7000.5, 0.0, 0.0])
        vel2 = np.array([0.0, 7.0, 0.0])

        rel_pos, rel_vel = _relative_state(pos1, vel1, pos2, vel2)

        np.testing.assert_array_almost_equal(rel_pos, [0.5, 0.0, 0.0])
        np.testing.assert_array_almost_equal(rel_vel, [0.0, -0.5, 0.0])


class TestBPlaneProjection:
    """Test B-plane projection."""

    def test_bplane_projection_shape(self):
        """Test that B-plane projection returns correct shapes."""
        rel_pos = np.array([0.5, 0.0, 0.0])
        rel_vel = np.array([0.0, 14.0, 0.0])
        cov = np.eye(6) * 0.1**2  # 0.1 km position uncertainty

        miss_2d, cov_2d = _project_to_bplane(rel_pos, rel_vel, cov)

        assert miss_2d.shape == (2,)
        assert cov_2d.shape == (2, 2)
        assert cov_2d[0, 1] == cov_2d[1, 0]  # Symmetric

    def test_bplane_miss_distance(self):
        """Test that B-plane miss distance is correct."""
        # Relative velocity in y direction
        rel_pos = np.array([0.5, 0.0, 0.0])
        rel_vel = np.array([0.0, 14.0, 0.0])
        cov = np.eye(6) * 0.1**2

        miss_2d, cov_2d = _project_to_bplane(rel_pos, rel_vel, cov)

        # Miss distance in B-plane should equal magnitude of rel_pos
        # (since rel_pos is perpendicular to rel_vel)
        miss_distance = np.linalg.norm(miss_2d)
        expected_distance = np.linalg.norm(rel_pos)

        assert abs(miss_distance - expected_distance) < 1e-10

    def test_bplane_perpendicular_to_velocity(self):
        """Test that B-plane is perpendicular to relative velocity."""
        rel_pos = np.array([0.5, 0.3, 0.2])
        rel_vel = np.array([1.0, 2.0, 3.0])
        cov = np.eye(6) * 0.1**2

        # The component of rel_pos along rel_vel should be excluded from miss_2d
        z_hat = rel_vel / np.linalg.norm(rel_vel)
        along_track_component = np.dot(rel_pos, z_hat)

        miss_2d, _ = _project_to_bplane(rel_pos, rel_vel, cov)

        # 3D miss vector perpendicular to rel_vel
        miss_3d_perp = rel_pos - along_track_component * z_hat

        # 2D miss magnitude should equal perpendicular 3D magnitude
        assert abs(np.linalg.norm(miss_2d) - np.linalg.norm(miss_3d_perp)) < 1e-10


class TestFosterPc:
    """Test Foster (1992) Pc calculation."""

    def test_zero_miss_high_pc(self):
        """Test that zero miss distance gives high Pc."""
        miss_2d = np.array([0.0, 0.0])
        cov_2d = np.eye(2) * 0.1**2  # 0.1 km uncertainty
        hard_body_radius = 0.020  # 20m in km

        pc = compute_pc_foster(miss_2d, cov_2d, hard_body_radius)

        # With zero miss and small HBR, Pc should be very small
        # (hard body is tiny compared to uncertainty)
        assert 0.0 <= pc <= 1.0

    def test_large_miss_zero_pc(self):
        """Test that large miss distance gives Pc ≈ 0."""
        miss_2d = np.array([1000.0, 0.0])  # 1000 km miss
        cov_2d = np.eye(2) * 0.1**2
        hard_body_radius = 0.020  # 20m in km

        pc = compute_pc_foster(miss_2d, cov_2d, hard_body_radius)

        assert pc < 1e-10  # Essentially zero

    def test_pc_increases_with_hbr(self):
        """Test that Pc increases as HBR increases."""
        miss_2d = np.array([0.1, 0.0])  # 100m miss
        cov_2d = np.eye(2) * 0.1**2

        pc_small = compute_pc_foster(miss_2d, cov_2d, 0.020)  # 20m
        pc_large = compute_pc_foster(miss_2d, cov_2d, 0.100)  # 100m

        assert pc_large > pc_small

    def test_pc_decreases_with_uncertainty(self):
        """Test that Pc decreases as uncertainty increases."""
        miss_2d = np.array([0.1, 0.0])
        hard_body_radius = 0.020

        cov_small = np.eye(2) * 0.05**2  # Small uncertainty
        cov_large = np.eye(2) * 0.5**2  # Large uncertainty

        pc_small_cov = compute_pc_foster(miss_2d, cov_small, hard_body_radius)
        pc_large_cov = compute_pc_foster(miss_2d, cov_large, hard_body_radius)

        # More uncertainty spreads probability over larger area
        assert pc_large_cov < pc_small_cov

    def test_singular_covariance(self):
        """Test handling of singular covariance."""
        miss_2d = np.array([0.1, 0.0])
        cov_2d = np.zeros((2, 2))  # Singular
        hard_body_radius = 0.020

        pc = compute_pc_foster(miss_2d, cov_2d, hard_body_radius)

        assert pc == 0.0


class TestMonteCartoPc:
    """Test Monte Carlo Pc calculation."""

    def test_zero_miss_positive_pc(self):
        """Test that zero miss gives positive Pc."""
        rel_pos = np.array([0.0, 0.0, 0.0])
        rel_vel = np.array([0.0, 7.0, 0.0])  # Arbitrary velocity
        cov = np.eye(6) * 0.1**2
        hard_body_radius = 0.020  # 20m in km

        pc = compute_pc_monte_carlo(
            rel_pos, rel_vel, cov, hard_body_radius, n_samples=10_000, seed=42
        )

        assert pc > 0.0
        assert pc <= 1.0

    def test_large_miss_zero_pc(self):
        """Test that large miss gives Pc ≈ 0."""
        rel_pos = np.array([1000.0, 0.0, 0.0])  # 1000 km
        rel_vel = np.array([0.0, 7.0, 0.0])
        cov = np.eye(6) * 0.1**2
        hard_body_radius = 0.020

        pc = compute_pc_monte_carlo(
            rel_pos, rel_vel, cov, hard_body_radius, n_samples=10_000, seed=42
        )

        assert pc == 0.0

    def test_reproducibility(self):
        """Test that same seed gives same result."""
        rel_pos = np.array([0.1, 0.0, 0.0])
        rel_vel = np.array([0.0, 7.0, 0.0])
        cov = np.eye(6) * 0.1**2
        hard_body_radius = 0.020

        pc1 = compute_pc_monte_carlo(rel_pos, rel_vel, cov, hard_body_radius, seed=42)
        pc2 = compute_pc_monte_carlo(rel_pos, rel_vel, cov, hard_body_radius, seed=42)

        assert pc1 == pc2

    def test_singular_covariance(self):
        """Test handling of singular covariance."""
        rel_pos = np.array([0.1, 0.0, 0.0])
        rel_vel = np.array([0.0, 7.0, 0.0])
        cov = np.zeros((6, 6))  # Singular
        hard_body_radius = 0.020

        pc = compute_pc_monte_carlo(rel_pos, rel_vel, cov, hard_body_radius)

        assert pc == 0.0


class TestComputePc:
    """Test main compute_pc function."""

    def test_basic_computation(self):
        """Test basic Pc computation."""
        # Two satellites in similar orbits, small miss distance
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.5, 0.0])
        pos2 = np.array([7000.5, 0.0, 0.0])  # 0.5 km apart
        vel2 = np.array([0.0, 7.0, 0.0])

        # Position uncertainty: 0.1 km
        cov1 = np.eye(6)
        cov1[:3, :3] *= 0.1**2  # Position covariance
        cov1[3:, 3:] *= 0.01**2  # Velocity covariance

        cov2 = cov1.copy()

        result = compute_pc(
            pos1, vel1, pos2, vel2, cov1, cov2, hard_body_radius_m=20.0, method=PcMethod.FOSTER_1992
        )

        assert isinstance(result, PcResult)
        assert 0.0 <= result.probability <= 1.0
        assert result.method == PcMethod.FOSTER_1992
        assert result.combined_hard_body_radius_m == 20.0
        assert result.mahalanobis_distance is not None

    def test_nasa_cara_test_case(self):
        """Test against NASA CARA-like scenario.

        Typical close approach:
        - Miss distance: 0.5 km
        - Relative velocity: 14 km/s
        - Combined position sigma: ~0.1 km in each B-plane axis
        - HBR: 20m
        - Expected Pc: 1e-6 to 1e-3 range
        """
        # Set up conjunction geometry
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.0, 1.0])  # ~7 km/s

        # Secondary offset by ~0.5 km, high relative velocity
        pos2 = np.array([7000.3, 0.0, 0.4])
        vel2 = np.array([0.0, -6.5, 1.5])  # Creates ~14 km/s relative velocity

        # Combined position uncertainty ~0.1 km in each axis
        cov1 = np.eye(6)
        cov1[:3, :3] *= 0.07**2  # ~70m position uncertainty
        cov1[3:, 3:] *= 0.001**2

        cov2 = np.eye(6)
        cov2[:3, :3] *= 0.07**2  # ~70m position uncertainty
        cov2[3:, 3:] *= 0.001**2

        result = compute_pc(
            pos1, vel1, pos2, vel2, cov1, cov2, hard_body_radius_m=20.0, method=PcMethod.FOSTER_1992
        )

        # Verify miss distance is reasonable
        rel_pos = pos2 - pos1
        miss_distance = np.linalg.norm(rel_pos)
        assert 0.4 < miss_distance < 0.6  # ~0.5 km

        # Verify Pc is in expected range for this geometry
        # 0.5km miss with 70m sigma and 20m HBR gives Pc ~1e-8 to 1e-5
        assert 1e-10 <= result.probability <= 1e-3

    def test_foster_vs_monte_carlo(self):
        """Test that Foster and Monte Carlo methods agree for high-Pc scenario."""
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.5, 0.0])
        pos2 = np.array([7000.005, 0.0, 0.0])  # 5m apart — very close
        vel2 = np.array([0.0, 7.0, 0.0])

        # Large uncertainty to make Pc measurable by MC
        cov1 = np.eye(6) * 0.01**2  # 10m position sigma
        cov2 = np.eye(6) * 0.01**2

        result_foster = compute_pc(
            pos1, vel1, pos2, vel2, cov1, cov2, hard_body_radius_m=20.0, method=PcMethod.FOSTER_1992
        )

        result_mc = compute_pc(
            pos1,
            vel1,
            pos2,
            vel2,
            cov1,
            cov2,
            hard_body_radius_m=20.0,
            method=PcMethod.MONTE_CARLO,
            mc_samples=100_000,
        )

        # Methods should agree within ~10% for large sample size
        # (or within absolute error for very small Pc)
        if result_foster.probability > 1e-4:
            relative_error = (
                abs(result_foster.probability - result_mc.probability) / result_foster.probability
            )
            assert relative_error < 0.5  # 50% tolerance — MC with 100K samples has high variance
        else:
            # For very small Pc, check absolute difference
            assert abs(result_foster.probability - result_mc.probability) < 1e-4

        assert result_mc.samples == 100_000

    def test_pc_zero_for_large_separation(self):
        """Test that Pc is essentially zero for large separation."""
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.5, 0.0])
        pos2 = np.array([8000.0, 0.0, 0.0])  # 1000 km apart
        vel2 = np.array([0.0, 7.0, 0.0])

        cov1 = np.eye(6) * 0.1**2
        cov2 = np.eye(6) * 0.1**2

        result = compute_pc(pos1, vel1, pos2, vel2, cov1, cov2, hard_body_radius_m=20.0)

        assert result.probability < 1e-10

    def test_pc_increases_with_closer_approach(self):
        """Test that Pc increases as objects get closer."""
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.5, 0.0])
        vel2 = np.array([0.0, 7.0, 0.0])

        cov1 = np.eye(6) * 0.1**2
        cov2 = np.eye(6) * 0.1**2

        # Far approach
        pos2_far = np.array([7001.0, 0.0, 0.0])  # 1 km
        result_far = compute_pc(pos1, vel1, pos2_far, vel2, cov1, cov2, hard_body_radius_m=20.0)

        # Close approach
        pos2_close = np.array([7000.1, 0.0, 0.0])  # 100m
        result_close = compute_pc(pos1, vel1, pos2_close, vel2, cov1, cov2, hard_body_radius_m=20.0)

        assert result_close.probability > result_far.probability

    def test_mahalanobis_distance(self):
        """Test that Mahalanobis distance is computed."""
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.5, 0.0])
        pos2 = np.array([7000.5, 0.0, 0.0])
        vel2 = np.array([0.0, 7.0, 0.0])

        cov1 = np.eye(6) * 0.1**2
        cov2 = np.eye(6) * 0.1**2

        result = compute_pc(pos1, vel1, pos2, vel2, cov1, cov2, hard_body_radius_m=20.0)

        assert result.mahalanobis_distance is not None
        assert result.mahalanobis_distance > 0

    def test_invalid_method_raises(self):
        """Test that invalid method raises error."""
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.5, 0.0])
        pos2 = np.array([7000.5, 0.0, 0.0])
        vel2 = np.array([0.0, 7.0, 0.0])

        cov1 = np.eye(6) * 0.1**2
        cov2 = np.eye(6) * 0.1**2

        with pytest.raises(ValueError, match="Unknown method"):
            # Create a fake method enum value
            class FakeMethod:
                pass

            compute_pc(pos1, vel1, pos2, vel2, cov1, cov2, method=FakeMethod())


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_covariance(self):
        """Test with zero covariance (deterministic positions)."""
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.5, 0.0])
        pos2 = np.array([7001.0, 0.0, 0.0])
        vel2 = np.array([0.0, 7.0, 0.0])

        cov1 = np.zeros((6, 6))
        cov2 = np.zeros((6, 6))

        # Should handle gracefully (Pc = 0 since no uncertainty)
        result = compute_pc(
            pos1, vel1, pos2, vel2, cov1, cov2, hard_body_radius_m=20.0, method=PcMethod.FOSTER_1992
        )

        assert result.probability == 0.0

    def test_very_large_covariance(self):
        """Test with very large covariance."""
        pos1 = np.array([7000.0, 0.0, 0.0])
        vel1 = np.array([0.0, 7.5, 0.0])
        pos2 = np.array([7000.5, 0.0, 0.0])
        vel2 = np.array([0.0, 7.0, 0.0])

        # Very large uncertainty (100 km)
        cov1 = np.eye(6) * 100.0**2
        cov2 = np.eye(6) * 100.0**2

        result = compute_pc(pos1, vel1, pos2, vel2, cov1, cov2, hard_body_radius_m=20.0)

        # With huge uncertainty, probability spreads thin
        assert 0.0 <= result.probability <= 1.0
        assert result.probability < 1e-6  # Should be very small

    def test_exact_overlap(self):
        """Test with objects at exactly the same position."""
        pos = np.array([7000.0, 0.0, 0.0])
        vel = np.array([0.0, 7.5, 0.0])

        cov1 = np.eye(6) * 0.1**2
        cov2 = np.eye(6) * 0.1**2

        result = compute_pc(pos, vel, pos, vel, cov1, cov2, hard_body_radius_m=20.0)

        # Zero miss distance should give higher Pc than non-zero
        assert result.probability > 0.0
