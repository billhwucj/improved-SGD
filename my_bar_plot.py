import matplotlib.pyplot as plt

# Sample data
categories = ['Original', 'Size', 'Opacity', 'Brightness']
# 294.68MB, b1=29.47MB/s, b2=9.82MB/s
b1_SSIM_set=[0.6250, 0.6016, 0.6335, 0.5709] # for avg SSIM
b2_SSIM_set=[0.5517, 0.5702, 0.5871, 0.4691]

b1_qoe_SSIM_set=[1.4193, 1.4431, 1.5791, 1.3703] # for qoe SSIM
b2_qoe_SSIM_set=[1.2915, 1.4280, 1.6135, 1.2041]

b1_PSNR_set=[21.8607, 18.3655, 19.5228, 15.1983] # for avg PSNR
b2_PSNR_set=[16.6587, 18.0016, 18.2012, 11.9712]

b1_qoe_PSNR_set=[61.9710, 59.3119, 62.3368, 50.7209] # for qoe PSNR
b2_qoe_PSNR_set=[53.0988, 58.7773, 61.8947, 44.3827]

# Bar width
bar_width = 0.4

# Positions of the bars
positions1 = range(len(categories))
positions2 = [p + bar_width for p in positions1]

plt.figure(figsize=(10, 6)) 

# Create the bar plots
# plt.bar(positions1, b1_SSIM_set, width=bar_width, color='skyblue', label='29.47MB/s', edgecolor='black', linewidth=1.5)
# plt.bar(positions2, b2_SSIM_set, width=bar_width, color='orange', label='9.82MB/s', edgecolor='black', linewidth=1.5)

plt.bar(positions1, b1_qoe_SSIM_set, width=bar_width, color='skyblue', label='29.47MB/s', edgecolor='black', linewidth=1.5)
plt.bar(positions2, b2_qoe_SSIM_set, width=bar_width, color='orange', label='9.82MB/s', edgecolor='black', linewidth=1.5)

# plt.bar(positions1, b1_PSNR_set, width=bar_width, color='skyblue', label='29.47MB/s', edgecolor='black', linewidth=1.5)
# plt.bar(positions2, b2_PSNR_set, width=bar_width, color='orange', label='9.82MB/s', edgecolor='black', linewidth=1.5)

# plt.bar(positions1, b1_qoe_PSNR_set, width=bar_width, color='skyblue', label='29.47MB/s', edgecolor='black', linewidth=1.5)
# plt.bar(positions2, b2_qoe_PSNR_set, width=bar_width, color='orange', label='9.82MB/s', edgecolor='black', linewidth=1.5)

# Add a dashed baseline for avg SSIM
# plt.axhline(y=0.5862, color='black', linestyle='--', linewidth=1.5, label='Baseline (29.47MB/s)')
# plt.axhline(y=0.4820, color='black', linestyle='-.', linewidth=1.5, label='Baseline (9.82MB/s)')
# Add a dashed baseline for qoe SSIM
plt.axhline(y=0.9980, color='black', linestyle='--', linewidth=1.5, label='Baseline (29.47MB/s)')
plt.axhline(y=0.7349, color='black', linestyle='-.', linewidth=1.5, label='Baseline (9.82MB/s)')
# Add a dashed baseline for avg PSNR
# plt.axhline(y=23.0974, color='black', linestyle='--', linewidth=1.5, label='Baseline (29.47MB/s)')
# plt.axhline(y=21.0890, color='black', linestyle='-.', linewidth=1.5, label='Baseline (9.82MB/s)')
# Add a dashed baseline for qoe PSNR
# plt.axhline(y=58.9944, color='black', linestyle='--', linewidth=1.5, label='Baseline (29.47MB/s)')
# plt.axhline(y=53.2626, color='black', linestyle='-.', linewidth=1.5, label='Baseline (9.82MB/s)')

# Add titles and labels
# plt.title('Measurement Result of Average SSIM', fontsize=24)
# plt.title('Measurement Result of QoE(SSIM)', fontsize=24)
# plt.title('Measurement Result of Average PSNR', fontsize=24)
# plt.title('Measurement Result of QoE(PSNR)', fontsize=24)
plt.xlabel('Utility', fontsize=22)
# plt.ylabel('SSIM', fontsize=22)
# plt.ylabel('PSBR(dB)', fontsize=22)
plt.ylabel('QoE(SSIM)($s^{-1}$)', fontsize=22)
# plt.ylabel('QoE(PSBR)(dB/s)', fontsize=22)
plt.xticks([p + bar_width / 2 for p in positions1], categories, fontsize=20)  # Centering category labels
plt.yticks(fontsize=20)
plt.legend(fontsize=16, framealpha=1,loc='lower left')  # Add legend

# Save the plot as an image
# plt.savefig('./result/avg_ssim_bar_plot.png', dpi=300, bbox_inches='tight')  # Adjust DPI and bounding box if needed
plt.savefig('./result/qoe_ssim_bar_plot.png', dpi=300, bbox_inches='tight')  # Adjust DPI and bounding box if needed
# plt.savefig('./result/avg_psnr_bar_plot.png', dpi=300, bbox_inches='tight')  # Adjust DPI and bounding box if needed
# plt.savefig('./result/qoe_psnr_bar_plot.png', dpi=300, bbox_inches='tight')  # Adjust DPI and bounding box if needed

plt.close()  # Close the figure to free memory
