document.addEventListener('DOMContentLoaded', function () {
    const imageModalElement = document.getElementById('imageGalleryModal');
    if (!imageModalElement) {
        // console.log("Image gallery modal not found on this page.");
        return;
    }

    const imageModal = new bootstrap.Modal(imageModalElement);
    const modalImageDisplay = document.getElementById('modalImageDisplay');
    const modalImageCounter = document.getElementById('modalImageCounter');
    const modalImageFilenameDisplay = document.getElementById('modalImageFilenameDisplay'); // For filename
    const modalPrevImageBtn = document.getElementById('modalPrevImage');
    const modalNextImageBtn = document.getElementById('modalNextImage');
    
    let currentImageIndex = 0;
    let currentPropertyImages = []; // Holds {url, filename} for the currently selected property

    // Delegated event listener for thumbnails (if added dynamically or for multiple galleries)
    document.body.addEventListener('click', function(event) {
        const thumbnail = event.target.closest('.property-image-thumbnail');
        if (!thumbnail) return;

        event.preventDefault(); // Prevent any default action if thumbnail is a link

        const imageUrlsData = thumbnail.dataset.imageUrls;
        const imageFilenamesData = thumbnail.dataset.imageFilenames;
        const initialIndex = parseInt(thumbnail.dataset.currentImageIndex || thumbnail.dataset.imageIndex || "0"); // imageIndex from detail, currentImageIndex from list

        if (!imageUrlsData) {
            console.error("Thumbnail clicked, but data-image-urls attribute is missing or empty.");
            return;
        }

        try {
            const urls = JSON.parse(imageUrlsData);
            const filenames = imageFilenamesData ? JSON.parse(imageFilenamesData) : [];
            
            currentPropertyImages = urls.map((url, index) => ({
                url: url,
                filename: filenames[index] || `Изображение ${index + 1}`
            }));
            
            currentImageIndex = initialIndex;
            if (currentImageIndex >= currentPropertyImages.length) currentImageIndex = 0;

            if (currentPropertyImages.length > 0) {
                updateModalImage();
                imageModal.show();
            } else {
                console.warn("No images found for this property in data attributes.");
            }
        } catch (e) {
            console.error("Error parsing image data from attributes:", e);
        }
    });

    function updateModalImage() {
        if (currentPropertyImages.length === 0 || currentImageIndex < 0 || currentImageIndex >= currentPropertyImages.length) {
            // Optionally hide modal or show placeholder if images become unavailable
            modalImageDisplay.src = ""; 
            modalImageDisplay.alt = "Нет изображения";
            if (modalImageFilenameDisplay) modalImageFilenameDisplay.textContent = "";
            if (modalImageCounter) modalImageCounter.textContent = "";
            return;
        }
        const currentImage = currentPropertyImages[currentImageIndex];
        modalImageDisplay.src = currentImage.url;
        modalImageDisplay.alt = currentImage.filename;
        
        if (modalImageFilenameDisplay) { // Display filename if element exists
            modalImageFilenameDisplay.textContent = currentImage.filename;
        }
        if (modalImageCounter) {
            modalImageCounter.textContent = `Фото ${currentImageIndex + 1} из ${currentPropertyImages.length}`;
        }

        if (modalPrevImageBtn) modalPrevImageBtn.disabled = (currentImageIndex === 0);
        if (modalNextImageBtn) modalNextImageBtn.disabled = (currentImageIndex === currentPropertyImages.length - 1);
    }

    if(modalPrevImageBtn) {
        modalPrevImageBtn.addEventListener('click', function () {
            if (currentImageIndex > 0) {
                currentImageIndex--;
                updateModalImage();
            }
        });
    }

    if(modalNextImageBtn) {
        modalNextImageBtn.addEventListener('click', function () {
            if (currentImageIndex < currentPropertyImages.length - 1) {
                currentImageIndex++;
                updateModalImage();
            }
        });
    }
});
