import pygame
def load_animation(directory, start_frame, frame_count, alpha=255, intro = False, loadCompressed = False, size = [854,480]):
    list_anim = []


    for x in range(frame_count):
        if not loadCompressed:
            x = x + start_frame
            im_dir = directory + "/" + (4 - len(str(x))) * "0" + str(x) + ".png"

            im = pygame.image.load(im_dir).convert_alpha()
            im = pygame.transform.scale(im, size)
            list_anim.append(im)

        
        introZoomFactor = 15

        if intro:
            if x - start_frame > frame_count-introZoomFactor:
                i = (x - start_frame) - (frame_count-introZoomFactor)
                i = (0.5 * (i/introZoomFactor) ** 4) + 1
                size = list(im.get_size())
                size[0] *= i
                size[1] *= i

                im = pygame.transform.scale(im, size)

        if alpha != 255:
            im2 = pygame.Surface(im.get_size())
            im2.fill((0, 0, 0))
            im.set_alpha(alpha)
            im2.blit(im, (0, 0))
            list_anim.append(im2)
        else:
            list_anim.append(im)

    return list_anim
