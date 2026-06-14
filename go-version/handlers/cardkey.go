package handlers

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"

	"my-shop/models"
)

type CardKeyHandler struct {
	DB *gorm.DB
}

func (h *CardKeyHandler) Import(c *gin.Context) {
	var req struct {
		ProductID uint   `json:"product_id" binding:"required"`
		Keys      string `json:"keys" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var product models.Product
	if err := h.DB.First(&product, req.ProductID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "商品不存在"})
		return
	}

	lines := strings.Split(strings.TrimSpace(req.Keys), "\n")
	var imported int
	for _, line := range lines {
		key := strings.TrimSpace(line)
		if key == "" {
			continue
		}
		h.DB.Create(&models.CardKey{
			ProductID: req.ProductID,
			Key:       key,
			Status:    models.CardKeyAvailable,
		})
		imported++
	}

	c.JSON(http.StatusOK, gin.H{"message": "导入成功", "count": imported})
}

func (h *CardKeyHandler) List(c *gin.Context) {
	productID, _ := parseInt(c.Query("product_id"), 0)
	status := c.Query("status")

	query := h.DB
	if productID > 0 {
		query = query.Where("product_id = ?", productID)
	}
	if status != "" {
		query = query.Where("status = ?", status)
	}

	var keys []models.CardKey
	query.Order("id desc").Find(&keys)
	c.JSON(http.StatusOK, keys)
}

func (h *CardKeyHandler) Delete(c *gin.Context) {
	id, _ := parseInt(c.Param("id"), 0)
	h.DB.Delete(&models.CardKey{}, id)
	c.JSON(http.StatusOK, gin.H{"message": "已删除"})
}

func (h *CardKeyHandler) DeleteByProduct(c *gin.Context) {
	productID, _ := parseInt(c.Param("id"), 0)
	h.DB.Where("product_id = ?", productID).Delete(&models.CardKey{})
	c.JSON(http.StatusOK, gin.H{"message": "已清空"})
}

func (h *CardKeyHandler) ExportSold(c *gin.Context) {
	productID, _ := parseInt(c.Query("product_id"), 0)
	query := h.DB.Where("status = ?", models.CardKeySold)
	if productID > 0 {
		query = query.Where("product_id = ?", productID)
	}

	var keys []models.CardKey
	query.Order("sold_at desc").Find(&keys)

	var lines []string
	for _, k := range keys {
		lines = append(lines, k.Key)
	}

	c.Header("Content-Type", "text/plain; charset=utf-8")
	c.String(http.StatusOK, strings.Join(lines, "\n"))
}
