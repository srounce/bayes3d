"""
# Trimesh to Gaussians
> Pretty much self-explanatory

**Example:**
```python
from bayes3d._mkl.trimesh_to_gaussians import (
    patch_trimesh,
    uniformly_sample_from_mesh,
    ellipsoid_embedding,
    get_mean_colors,
    pack_transform,
    transform_from_gaussian
)
import trimesh
import numpy as np
import jax.numpy as jnp
import jax
from jax import jit, vmap
from sklearn.mixture import GaussianMixture
from bayes3d._mkl.utils import keysplit

# SEED
key = jax.random.PRNGKey(0)

# LOAD MESH
# -------------------
mesh = load_mesh(...)
mesh = patch_trimesh(mesh)

# SAMPLE FROM MESH
# ----------------
key = keysplit(key)
n = 20_000
xs, cs = uniformly_sample_from_mesh(key, n, mesh, with_color=True)

# GMM CONFIG
# ----------
key = keysplit(key)
n_components = 150
noise        = 0.0;
X            = xs + np.random.randn(*xs.shape)*noise
means_init   = np.array(uniformly_sample_from_mesh(key, n_components, mesh, with_color=False)[0]);

# FIT THE GMM
# -----------
gm = GaussianMixture(n_components=n_components,
                     tol=1e-3, max_iter=100,
                     covariance_type="full",
                     means_init=means_init).fit(X)

mus        = gm.means_
covs       = gm.covariances_
labels     = gm.predict(X)
choleskys  = vmap(ellipsoid_embedding)(covs)
transforms = vmap(transform_from_gaussian, (0,0,None))(mus, covs, 2.0)
mean_colors, nums = get_mean_colors(cs, gm.n_components, labels)
```
"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb.

# %% auto 0
import jax
import jax.numpy as jnp
import jaxlib
import numpy as np
import trimesh
from jax import jit, vmap

from bayes3d._mkl.utils import *

__all__ = [
    "Array",
    "Shape",
    "FaceIndex",
    "FaceIndices",
    "Array3",
    "Array2",
    "ArrayNx2",
    "ArrayNx3",
    "Matrix",
    "PrecisionMatrix",
    "CovarianceMatrix",
    "SquareMatrix",
    "Vector",
    "compute_area_and_normals",
    "area_of_triangle",
    "patch_trimesh",
    "texture_uv_basis",
    "uv_to_color",
    "barycentric_to_mesh",
    "sample_from_face",
    "sample_from_mesh",
    "get_colors_from_mesh",
    "uniformly_sample_from_mesh",
    "get_cluster_counts",
    "get_cluster_colors",
    "get_mean_colors",
    "ellipsoid_embedding",
    "pack_transform",
    "transform_from_gaussian",
    "create_ellipsoid_trimesh",
]

# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 2
_doc_ = """
# Trimesh to Gaussians
> Pretty much self-explanatory

**Example:**
```python
from bayes3d._mkl.trimesh_to_gaussians import (
    patch_trimesh,
    uniformly_sample_from_mesh,
    ellipsoid_embedding,
    get_mean_colors,
    pack_transform,
    transform_from_gaussian
)
import trimesh
import numpy as np
import jax.numpy as jnp
import jax
from jax import jit, vmap
from sklearn.mixture import GaussianMixture
from bayes3d._mkl.utils import keysplit

# SEED
key = jax.random.PRNGKey(0)

# LOAD MESH
# -------------------
mesh = load_mesh(...)
mesh = patch_trimesh(mesh)

# SAMPLE FROM MESH
# ----------------
key = keysplit(key)
n = 20_000
xs, cs = uniformly_sample_from_mesh(key, n, mesh, with_color=True)

# GMM CONFIG
# ----------
key = keysplit(key)
n_components = 150
noise        = 0.0;
X            = xs + np.random.randn(*xs.shape)*noise
means_init   = np.array(uniformly_sample_from_mesh(key, n_components, mesh, with_color=False)[0]);

# FIT THE GMM
# -----------
gm = GaussianMixture(n_components=n_components,
                     tol=1e-3, max_iter=100,
                     covariance_type="full",
                     means_init=means_init).fit(X)

mus        = gm.means_
covs       = gm.covariances_
labels     = gm.predict(X)
choleskys  = vmap(ellipsoid_embedding)(covs)
transforms = vmap(transform_from_gaussian, (0,0,None))(mus, covs, 2.0)
mean_colors, nums = get_mean_colors(cs, gm.n_components, labels)
```
"""

# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 3
Array = np.ndarray | jax.Array
Shape = int | tuple[int, ...]
FaceIndex = int
FaceIndices = Array
Array3 = Array
Array2 = Array
ArrayNx2 = Array
ArrayNx3 = Array
Matrix = jaxlib.xla_extension.ArrayImpl
PrecisionMatrix = Matrix
CovarianceMatrix = Matrix
SquareMatrix = Matrix
Vector = Array


# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 5
def area_of_triangle(a: Array3, b: Array3, c: Array3 = jnp.zeros(3)):
    """Computes the area of a triangle spanned by a,b[,c]."""
    x = a - c
    y = b - c
    w = jnp.linalg.norm(x)
    h = jnp.linalg.norm(y - jnp.dot(x, y) / w**2 * x)
    area = w * h / 2

    return area


def _compute_area_and_normal(f, vertices):
    a = vertices[f[1]] - vertices[f[0]]
    b = vertices[f[2]] - vertices[f[0]]
    area = area_of_triangle(a, b)
    normal = jnp.cross(a, b)
    return area, normal


compute_area_and_normals = jit(vmap(_compute_area_and_normal, (0, None)))


# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 6
def patch_trimesh(mesh: trimesh.base.Trimesh):
    """
    Return a patched copy of a trimesh object, and
    ensure it to have a texture and the following attributes:
     - `mesh.visual.uv`
     - `copy.visual.material.to_color`
    """
    patched_mesh = mesh.copy()
    if isinstance(mesh.visual, trimesh.visual.color.ColorVisuals):
        patched_mesh.visual = mesh.visual.to_texture()
    elif isinstance(mesh.visual, trimesh.visual.texture.TextureVisuals):
        pass

    return patched_mesh


def texture_uv_basis(face_idx: Array, mesh):
    """
    Takes a face index and returns the three uv-vectors
    spanning the face in texture space.
    """
    return mesh.visual.uv[mesh.faces[face_idx]]


def uv_to_color(uv: ArrayNx2, mesh):
    """Takes texture-uv coordinates and returns the corresponding color."""
    return mesh.visual.material.to_color(uv)


# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 7
def barycentric_to_mesh(p: Array3, i: FaceIndex, mesh):
    """Converts a point in barycentric coordinates `p` on a face `i` to a 3d point on the mesh."""
    x = jnp.sum(p[:, None] * mesh.vertices[mesh.faces[i]], axis=0)
    return x


def sample_from_face(key, n, i, mesh):
    """
    Sample random points `xs`, barycentric coordinates `ps`, and
    face indices `fs` from a mesh.
    """
    _, key = keysplit(key, 1, 1)
    ps = jax.random.dirichlet(key, jnp.ones(3), (n,)).reshape((n, 3, 1))
    xs = jnp.sum(ps * mesh.vertices[mesh.faces[i]], axis=1)
    return xs, ps


def sample_from_mesh(key, n, mesh):
    """
    Returns random points `xs`, barycentric coordinates `ps`, and
    face indices `fs` from a mesh.
    """
    _, keys = keysplit(key, 1, 2)

    # Sample `n` faces from the mesh with
    # probability proportional to their area.
    areas, _ = compute_area_and_normals(mesh.faces, mesh.vertices)
    fs = jax.random.categorical(keys[0], jnp.log(areas), shape=(n,))

    # Sample barycentric coordinates `bs` for each sampled face
    # and compute the corresponding world coordinates `xs`.
    ps = jax.random.dirichlet(keys[1], jnp.ones(3), (n,)).reshape((n, 3, 1))
    xs = jnp.sum(ps * mesh.vertices[mesh.faces[fs]], axis=1)
    return xs, ps, fs


def get_colors_from_mesh(ps: ArrayNx3, fs: FaceIndices, mesh):
    """
    Returns the colors of the points on the mesh given
    their barycentric coordinates `ps` and face indices `fs`.
    """
    uvs = jnp.sum(ps * texture_uv_basis(fs, mesh), axis=1)
    cs = uv_to_color(uvs, mesh) / 255
    return cs


# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 9
def uniformly_sample_from_mesh(key, n, mesh, with_color=True):
    """Uniformly sample `n` points and optionally their color on the surface from a mesh."""
    xs, ps, fs = sample_from_mesh(key, n, mesh)

    if with_color:
        cs = get_colors_from_mesh(ps, fs, mesh)
    else:
        cs = jnp.full((n, 3), 0.5)

    return xs, cs


# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 10
def get_cluster_counts(m, labels):
    nums = []
    for label in range(m):
        nums.append(np.sum(labels == label))
    return np.array(nums)


# |export
def get_cluster_colors(cs, m, labels):
    colors = []
    for label in range(m):
        colors.append(cs[labels == label])
    return colors


# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 11
def get_mean_colors(cs, n, labels):
    mean_colors = []
    nums = []
    for label in range(n):
        idx = labels == label
        num = np.sum(idx)
        if num == 0:
            c = np.array([0.5, 0.5, 0.5, 0.0])
        else:
            c = np.mean(cs[idx], axis=0)
        nums.append(num)
        mean_colors.append(c)

    return np.array(mean_colors), np.array(nums)


# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 12
def ellipsoid_embedding(cov: CovarianceMatrix) -> Matrix:
    """Returns A with cov = A@A.T"""
    sigma, U = jnp.linalg.eigh(cov)
    D = jnp.diag(jnp.sqrt(sigma))
    return U @ D @ jnp.linalg.inv(U)


# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 13
def pack_transform(x, A, scale=1.0):
    B = scale * A
    return jnp.array(
        [
            [B[0, 0], B[0, 1], B[0, 2], x[0]],
            [B[1, 0], B[1, 1], B[1, 2], x[1]],
            [B[2, 0], B[2, 1], B[2, 2], x[2]],
            [0.0, 0.0, 0.0, 1.0],
        ]
    ).T


def transform_from_gaussian(
    mu: Vector, cov: CovarianceMatrix = jnp.eye(3), scale=1.0
) -> Matrix:
    """Returns an affine linear transformation 4x4 matrix from a Gaussian."""
    A = ellipsoid_embedding(cov)
    B = scale * A
    return jnp.array(
        [
            [B[0, 0], B[0, 1], B[0, 2], mu[0]],
            [B[1, 0], B[1, 1], B[1, 2], mu[1]],
            [B[2, 0], B[2, 1], B[2, 2], mu[2]],
            [0.0, 0.0, 0.0, 1.0],
        ]
    ).T


# %% ../../scripts/_mkl/notebooks/05 - Trimesh to Gaussians.ipynb 14
def create_ellipsoid_trimesh(covariance_matrix, num_points=10, scale=0.02):
    # Create a sphere
    u = np.linspace(0, 2 * np.pi, num_points)
    v = np.linspace(0, np.pi, num_points)
    x = np.outer(np.cos(u), np.sin(v))
    y = np.outer(np.sin(u), np.sin(v))
    z = np.outer(np.ones(np.size(u)), np.cos(v))

    # Transform the sphere to the ellipsoid
    sigma, U = np.linalg.eig(covariance_matrix)
    D = np.diag(np.sqrt(sigma))
    ellipsoid = (
        U @ D @ np.linalg.inv(U) @ np.vstack([x.flatten(), y.flatten(), z.flatten()])
    )

    # Reshape the ellipsoid to match the shape of the original sphere vertices
    ellipsoid = ellipsoid.T.reshape(num_points, num_points, 3)

    # Create mesh data
    mesh_vertices = scale * ellipsoid.reshape(-1, 3)
    mesh_faces = []
    for i in range(num_points - 1):
        for j in range(num_points - 1):
            v1 = i * num_points + j
            v2 = v1 + 1
            v3 = (i + 1) * num_points + j
            v4 = v3 + 1
            mesh_faces.append([v1, v2, v3])
            mesh_faces.append([v2, v4, v3])

    mesh_faces = np.array(mesh_faces)

    # Create a trimesh object
    trimesh_mesh = trimesh.Trimesh(vertices=mesh_vertices, faces=mesh_faces)

    return trimesh_mesh
