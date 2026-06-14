package database

import (
	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
	"my-shop/models"
)

var DB *gorm.DB

func Init(dbPath string) error {
	var err error
	DB, err = gorm.Open(sqlite.Open(dbPath+"?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)"), &gorm.Config{})
	if err != nil {
		return err
	}
	return DB.AutoMigrate(
		&models.User{},
		&models.ProductCategory{},
		&models.Product{},
		&models.BlindBoxPool{},
		&models.CardKey{},
		&models.Coupon{},
		&models.UserCoupon{},
		&models.Order{},
		&models.OrderItem{},
		&models.Review{},
	)
}
