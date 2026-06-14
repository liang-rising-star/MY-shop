package models

import "time"

type ProductType string

const (
	ProductNormal   ProductType = "normal"
	ProductBlindBox ProductType = "blindbox"
	ProductTimed    ProductType = "timed"
)

type Product struct {
	ID           uint          `gorm:"primaryKey" json:"id"`
	Name         string        `gorm:"size:200;not null" json:"name"`
	Description  string        `gorm:"type:text" json:"description"`
	Price        float64       `gorm:"not null" json:"price"`
	CategoryID   uint          `gorm:"index" json:"category_id"`
	Category     ProductCategory `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
	ImageURL     string        `gorm:"size:500" json:"image_url"`
	Type         ProductType   `gorm:"size:20;default:normal" json:"type"`
	Stock        int           `gorm:"default:-1" json:"stock"`
	TotalSold    int           `gorm:"default:0" json:"total_sold"`
	StartAt      *time.Time    `json:"start_at,omitempty"`
	EndAt        *time.Time    `json:"end_at,omitempty"`
	CreatedAt    time.Time     `json:"created_at"`
	UpdatedAt    time.Time     `json:"updated_at"`
}

type BlindBoxPool struct {
	ID          uint    `gorm:"primaryKey" json:"id"`
	ProductID   uint    `gorm:"index;not null" json:"product_id"`
	PrizeID     uint    `gorm:"not null" json:"prize_id"`
	Prize       Product `gorm:"foreignKey:PrizeID" json:"prize,omitempty"`
	Probability float64 `gorm:"not null" json:"probability"`
	CreatedAt   time.Time `json:"created_at"`
}
