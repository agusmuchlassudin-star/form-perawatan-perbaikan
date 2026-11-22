
st.markdown("""
<style>
.stats-container {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
    margin: 15px 0 25px 0;
}

.stat-card {
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #142c48, #1b4268);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 18px;
    padding: 25px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.25);
}

.stat-card.orange {
    background: linear-gradient(135deg, #a94f13, #f28c28);
}

.stat-card.blue {
    background: linear-gradient(135deg, #102d50, #1769aa);
}

.stat-card.green {
    background: linear-gradient(135deg, #124b4a, #16877b);
}

.stat-label {
    color: #d8e5f3;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.stat-number {
    color: white;
    font-size: 42px;
    font-weight: 800;
    margin: 12px 0 5px 0;
    letter-spacing: -1px;
}

.stat-description {
    color: #dbeafe;
    font-size: 12px;
}

.stat-icon {
    position: absolute;
    right: 22px;
    top: 22px;
    font-size: 38px;
    opacity: 0.85;
}

.stat-line {
    width: 45px;
    height: 4px;
    background: #f28c28;
    border-radius: 5px;
    margin-top: 14px;
}

@media (max-width: 700px) {
    .stats-container {
        grid-template-columns: 1fr;
    }
}
</style>

<div class="stats-container">

    <div class="stat-card blue">
        <div class="stat-icon">🚆</div>
        <div class="stat-label">Total Sarana</div>
        <div class="stat-number">582</div>
        <div class="stat-description">Total keseluruhan sarana</div>
        <div class="stat-line"></div>
    </div>

    <div class="stat-card orange">
        <div class="stat-icon">🚃</div>
        <div class="stat-label">Gerbong GD / GB</div>
        <div class="stat-number">527</div>
        <div class="stat-description">Jumlah sarana gerbong</div>
        <div class="stat-line" style="background:white;"></div>
    </div>

    <div class="stat-card green">
        <div class="stat-icon">📦</div>
        <div class="stat-label">Bagasi B</div>
        <div class="stat-number">55</div>
        <div class="stat-description">Jumlah sarana bagasi</div>
        <div class="stat-line" style="background:#a7f3d0;"></div>
    </div>

</div>
""", unsafe_allow_html=True)
