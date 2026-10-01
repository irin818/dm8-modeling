"""Only the final single Gaussian and opposing-sign DoG spatial models."""

import numpy as np
from scipy.optimize import lsq_linear


def projection_matrix(size: int, steps: int) -> np.ndarray:
    """Linear [15,225] operator: 360° rotations, bilinear valid-pixel column means."""
    if size != 15 or steps < 1:
        raise ValueError("Expected a 15x15 field and positive rotation count")
    yy, xx = np.mgrid[:size, :size].astype(float)
    xx -= size//2
    yy -= size//2
    matrix = np.zeros((size, size*size))
    for theta in 2*np.pi*np.arange(steps)/steps:
        sx = np.cos(theta)*xx-np.sin(theta)*yy+size//2
        sy = np.sin(theta)*xx+np.cos(theta)*yy+size//2
        valid = (sx >= -1e-12) & (sx <= size-1+1e-12) & (sy >= -1e-12) & (sy <= size-1+1e-12)
        sx, sy = np.clip(sx,0,size-1), np.clip(sy,0,size-1)
        x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
        dx, dy = sx-x0, sy-y0
        count = valid.sum(axis=0)
        for row, col in zip(*np.nonzero(valid), strict=True):
            scale = 1/(steps*count[col])
            for py, wy in ((y0[row,col],1-dy[row,col]),(min(y0[row,col]+1,size-1),dy[row,col])):
                for px, wx in ((x0[row,col],1-dx[row,col]),(min(x0[row,col]+1,size-1),dx[row,col])):
                    matrix[col,py*size+px] += scale*wy*wx
    return matrix


def rotational_profile(image: np.ndarray, projector: np.ndarray) -> np.ndarray:
    """Project [15,15] RF to [15] profile with valid-support renormalization."""
    valid = np.isfinite(image)
    denominator = projector @ valid.ravel().astype(float)
    return np.divide(projector @ np.nan_to_num(image).ravel(), denominator,
                     out=np.full(image.shape[1], np.nan), where=denominator > 1e-8)


def bounded_candidates(designs: np.ndarray, initial: np.ndarray, y: np.ndarray, limits: list) -> tuple[np.ndarray, np.ndarray]:
    """Solve fixed-grid bounded linear fits; prune using unconstrained SSE lower bounds."""
    low, high = np.array([x[0] for x in limits]), np.array([x[1] for x in limits])
    error = np.einsum("pni,pi->pn", designs, initial)-y
    lower_sse = np.einsum("pn,pn->p", error, error)
    feasible = np.all((initial >= low-1e-12) & (initial <= high+1e-12), axis=1)
    answer = initial.copy()
    sse = np.where(feasible,lower_sse,np.inf)
    for index in np.argsort(lower_sse):
        if lower_sse[index] >= np.min(sse)-1e-18:
            break
        if not feasible[index]:
            fit = lsq_linear(designs[index],y,bounds=(low,high),tol=1e-12,max_iter=100)
            answer[index] = fit.x
            sse[index] = float(np.sum((designs[index] @ fit.x-y)**2))
    if not np.isfinite(sse).any():
        raise RuntimeError("No bounded spatial fit succeeded")
    return answer, sse


def fit_models(profile: np.ndarray, config: dict) -> list[dict]:
    """Fit M1 and antagonistic M3 to the same [15] projection; widths in pixels."""
    finite = np.isfinite(profile)
    x = np.arange(-7,8)[finite]
    raw_y = profile[finite]
    if len(raw_y) < 7:
        raise ValueError("Too few supported projection points")
    scale = config["model_profile_abs_peak"]/max(float(np.max(np.abs(raw_y))),1e-12)
    y = raw_y*scale
    def grid(spec):
        """Inclusive fixed pixel-width grid; keeps frozen model selection reproducible."""
        low,high,step = spec
        return np.arange(low,high+step/2,step)
    widths1, widths2 = grid(config["center_sigma_grid_px"]), grid(config["surround_sigma_grid_px"])
    first = np.exp(-x[None,:]**2/(2*widths1[:,None]**2))
    second = np.exp(-x[None,:]**2/(2*widths2[:,None]**2))
    pairs = [(i,j) for i,a in enumerate(widths1) for j,b in enumerate(widths2)
             if b-a >= config["minimum_sigma_separation_px"]-1e-12]
    ones = np.ones_like(x)
    baseline, amplitude = config["model_baseline_bounds"], config["model_amplitude_bounds"]
    fits = []
    for model in ("M1","M3"):
        designs = (np.stack([np.column_stack((ones,g)) for g in first]) if model == "M1"
            else np.stack([np.column_stack((ones,first[i],second[j])) for i,j in pairs]))
        limits = [baseline, amplitude] if model == "M1" else [baseline,[amplitude[0],0],[0,amplitude[1]]]
        coefficients, sse_grid = bounded_candidates(designs,np.linalg.pinv(designs) @ y,y,limits)
        best = int(np.argmin(sse_grid))
        coef = coefficients[best]
        prediction = designs[best] @ coef
        sse = float(np.sum((y-prediction)**2))
        total = float(np.sum((y-y.mean())**2))
        n, k = len(y), 3 if model == "M1" else 5
        aic = n*np.log(max(sse/n,np.finfo(float).tiny))+2*k
        i,j = (best,None) if model == "M1" else pairs[best]
        fits.append({"model":model,"r2":1-sse/total if total > 0 else np.nan,
            "aic":float(aic),"aicc":float(aic+2*k*(k+1)/(n-k-1)),
            "bic":float(n*np.log(max(sse/n,np.finfo(float).tiny))+k*np.log(n)),
            "center_sigma_px":float(widths1[i]),"surround_sigma_px":None if j is None else float(widths2[j]),
            "baseline":float(coef[0]/scale),"center_amplitude":float(coef[1]/scale),
            "surround_amplitude":None if j is None else float(coef[2]/scale),
            "relative_surround_amplitude":None if j is None else float(coef[2]/abs(coef[1])) if abs(coef[1]) > 1e-12 else None,
            "profile_rescale_factor":scale,"prediction":(prediction/scale).tolist(),
            "fit_positions_px":x.tolist()})
    return fits
